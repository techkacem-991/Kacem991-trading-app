from flask import Flask, render_template_string
import requests

app = Flask(__name__)

SYMBOLS_TO_SCAN = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT", "NEARUSDT"
]

def scan_market():
    best_results = {}
    max_score = -1
    for symbol in SYMBOLS_TO_SCAN:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=30"
            res = requests.get(url, timeout=8) # زيادة المهلة إلى 8 ثوانٍ
            if res.status_code != 200:
                continue
            klines = res.json()
            if not klines or len(klines) < 20:
                continue
            
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            current_price = closes[-1]
            
            period = 14
            gains = sum([closes[-i] - closes[-i-1] for i in range(1, period + 1) if (closes[-i] - closes[-i-1]) >= 0])
            losses = sum([-(closes[-i] - closes[-i-1]) for i in range(1, period + 1) if (closes[-i] - closes[-i-1]) < 0])
            avg_gain = gains / period
            avg_loss = losses / period
            rsi = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))
            
            tr_list = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(closes))]
            last_atr = sum(tr_list[-14:]) / 14 if len(tr_list) >= 14 else current_price * 0.03
            
            win_prob = round(min(max(50 + (50 - abs(rsi - 50)), 45), 95), 1)
            
            # جعل الشرط يقبل أي نتيجة صالحة مؤقتاً لضمان ظهور بيانات
            if win_prob > max_score or not best_results:
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
        except Exception as e:
            print(f"Error in {symbol}: {e}")
            continue
    return best_results

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوت تداول العملات</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; text-align: center; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-top: 20px; text-align: right; }
        button { background: #22c55e; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        button:active { background: #16a34a; }
        .loading { color: #38bdf8; margin-top: 15px; }
    </style>
</head>
<body>
    <h2>📊 بوت التداول المستقل</h2>
    <p>اضغط لفحص السوق وجلب أفضل فرصة:</p>
    <button onclick="fetchSignal()">🔍 فحص السوق الآن</button>
    <div id="result" class="card" style="display:none;"></div>

    <script>
        function fetchSignal() {
            document.getElementById('result').style.display = 'block';
            document.getElementById('result').innerHTML = '<div class="loading">⏳ جاري فحص الأسواق وتحليل البيانات...</div>';
            
            fetch('/scan')
            .then(response => response.json())
            .then(data => {
                if(data.symbol) {
                    document.getElementById('result').innerHTML = `
                        <h3>🔥 أفضل فرصة: ${data.symbol}</h3>
                        <p>💵 السعر: $${data.price.toFixed(4)}</p>
                        <p>🎯 نسبة النجاح: <b>${data.win}%</b></p>
                        <p>📈 الهدف الأول (TP1): $${data.tp1.toFixed(4)}</p>
                        <p>🚀 الهدف الثاني (TP2): $${data.tp2.toFixed(4)}</p>
                        <p>🛑 وقف الخسارة (SL): $${data.sl.toFixed(4)}</p>
                        <p>📊 مؤشر RSI: ${data.rsi.toFixed(2)}</p>
                    `;
                } else {
                    document.getElementById('result').innerHTML = '<p>❌ لم يتم العثور على فرصة حالياً.</p>';
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

@app.route('/scan')
def scan():
    result = scan_market()
    return result

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
