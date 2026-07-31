from flask import Flask, render_template_string, jsonify
import requests

app = Flask(__name__)

SYMBOLS_TO_SCAN = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT", "NEARUSDT"
]

@app.route('/scan')
def scan_market():
    best_results = {}
    max_score = -1
    
    for symbol in SYMBOLS_TO_SCAN:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=25"
            res = requests.get(url, timeout=3)
            if res.status_code != 200:
                continue
            klines = res.json()
            if not klines or len(klines) < 15:
                continue
            
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            current_price = closes[-1]
            
            # حساب RSI سريع
            gains, losses = 0, 0
            for i in range(1, 15):
                diff = closes[-i] - closes[-i-1]
                if diff >= 0:
      @@ -44,8 +45,8 @@
                else:
                    losses -= diff
            avg_gain = gains / 14
            avg_loss = losses / 14
            rsi = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))
            
            # حساب ATR سريع
            tr_list = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(closes))]
            last_atr = sum(tr_list[-14:]) / 14 if len(tr_list) >= 14 else current_price * 0.03
            
            win_prob = round(min(max(50 + (50 - abs(rsi - 50)), 45), 95), 1)
            
            if win_prob > max_score:
                max_score = win_prob
                best_results = {
                    "symbol": symbol,
                    "price": current_price,
                    "win": win_prob,
                    "tp1": current_price + (2 * last_atr),
                    "tp2": current_price + (3.5 * last_atr),
                    "sl": current_price - (1.5 * last_atr),
                    "rsi": rsi
                }
        except:
            continue
            
    return jsonify(best_results)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوت تداول العملات - إشارات حية</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; text-align: center; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-top: 20px; text-align: right; border-right: 5px solid #22c55e; }
        button { background: #22c55e; color: white; border: none; padding: 14px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        button:active { background: #16a34a; }
        .loading { color: #38bdf8; margin-top: 15px; font-weight: bold; }
        .item { margin: 8px 0; font-size: 15px; }
    </style>
</head>
<body>
    <h2>📊 تداول مع قاسم</h2>
    <p>اضغط لفحص الأسواق الحية وجلب أقوى صفقة:</p>
    <button onclick="fetchSignal()">🔍 فحص السوق وجلب الصفقة</button>
    <div id="result" class="card" style="display:none;"></div>

    <script>
        function fetchSignal() {
            const resDiv = document.getElementById('result');
            resDiv.style.display = 'block';
            resDiv.innerHTML = '<div class="loading">⏳ جاري الاتصال المباشر بمنصة Binance...</div>';
            
            fetch('/scan')
            .then(response => response.json())
            .then(data => {
                if(data.symbol) {
                    resDiv.innerHTML = `
                        <h3 style="color: #22c55e; margin-top:0;">🔥 أفضل فرصة تداول حالياً</h3>
                        <div class="item">📌 <b>الزوج / العملة:</b> ${data.symbol}</div>
                        <div class="item">💵 <b>السعر الحالي:</b> $${data.price.toFixed(4)}</div>
                        <div class="item">🎯 <b>نسبة النجاح المتوقعة:</b> ${data.win}%</div>
                        <hr style="border:0; border-top:1px solid #334155; margin:12px 0;">
                        <div class="item" style="color: #38bdf8;">📈 <b>الهدف الأول (TP1):</b> $${data.tp1.toFixed(4)}</div>
                        <div class="item" style="color: #38bdf8;">🚀 <b>الهدف الثاني (TP2):</b> $${data.tp2.toFixed(4)}</div>
                        <div class="item" style="color: #ef4444;">🛑 <b>وقف الخسارة (SL):</b> $${data.sl.toFixed(4)}</div>
                        <hr style="border:0; border-top:1px solid #334155; margin:12px 0;">
                        <div class="item">📊 <b>مؤشر القوة النسبية (RSI):</b> ${data.rsi.toFixed(2)}</div>
                    `;
                } else {
                    resDiv.innerHTML = '<p style="color: #ef4444;">❌ لم يتم جلب البيانات، أعد المحاولة.</p>';
                }
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
