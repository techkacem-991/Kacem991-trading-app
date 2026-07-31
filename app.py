import threading
from flask import Flask, request, render_template_string, jsonify
import requests
import time
import schedule

app = Flask(__name__)

TELEGRAM_TOKEN = "8968850415:AAG9DwLeyHQ7iNuLmISdhnHnSh7m6us_PgQ"
CHAT_ID = "5723285644"

SYMBOLS_TO_SCAN = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT", "NEARUSDT",
    "RENDERUSDT", "FETUSDT", "LTCUSDT", "BCHUSDT",
    "ATOMUSDT", "ETCUSDT", "XLMUSDT", "FILUSDT", "ALGOUSDT", "ICPUSDT"
]
CHECK_INTERVAL_HOURS = 4

def send_telegram_with_multiple_buttons(text, symbols_list):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard_buttons = []
    for sym in symbols_list:
        button_row = [{"text": f"🟡 بايننس {sym}", "url": f"https://www.binance.com/en/trade/{sym}"}]
        keyboard_buttons.append(button_row)
    
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": keyboard_buttons}
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ خطأ في التيليجرام: {e}")

def send_telegram_single_button(text, symbol):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[{"text": f"🟡 بايننس {symbol}", "url": f"https://www.binance.com/en/trade/{symbol}"}]]}
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ خطأ: {e}")

def send_simple_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ خطأ: {e}")

def get_best_market_opportunity():
    best_data = {}
    max_score = -1

    for symbol in SYMBOLS_TO_SCAN:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=30"
            res = requests.get(url, timeout=3)
            if res.status_code != 200:
                continue
            klines = res.json()
            if not klines or len(klines) < 20:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            current_price = closes[-1]

            # حساب RSI بدقة وسرعة
            gains, losses = 0, 0
            for i in range(1, 15):
                diff = closes[-i] - closes[-i-1]
                if diff >= 0:
                    gains += diff
                else:
                    losses -= diff
            avg_gain = gains / 14
            avg_loss = losses / 14
            last_rsi = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))

            # حساب ATR
            tr_list = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(closes))]
            last_atr = sum(tr_list[-14:]) / 14 if len(tr_list) >= 14 else current_price * 0.03

            win_probability = round(min(max(50 + (50 - abs(last_rsi - 50)), 45), 95), 1)

            if win_probability > max_score:
                max_score = win_probability
                dynamic_sl = current_price - (1.5 * last_atr)
                tp1 = current_price + (2 * last_atr)
                tp2 = current_price + (3.5 * last_atr)
                if dynamic_sl >= current_price:
                    dynamic_sl = current_price * 0.97

                best_data = {
                    "symbol": symbol,
                    "price": current_price,
                    "win": win_probability,
                    "tp1": tp1,
                    "tp2": tp2,
                    "sl": dynamic_sl,
                    "rsi": last_rsi
                }
        except:
            continue

    return best_data if best_data else None

def analyze_and_send_signals():
    reports = []
    current_report = "🧠 <b>التقرير الذكي والمتقدم للعملات</b>\n" + "=" * 25 + "\n\n"
    current_batch_symbols = []
    count = 0

    for symbol in SYMBOLS_TO_SCAN:
        data = get_best_market_opportunity()
        if data:
            current_report += f"📌 <b>العملة: {symbol}</b>\n"
            current_report += f"• <b>السعر:</b> ${data['price']:.4f}\n"
            current_report += f"• <b>النسبة:</b> <b>{data['win']}%</b> 🎯\n" + "-" * 20 + "\n\n"
            current_batch_symbols.append(symbol)
            count += 1
            if count == 5:
                reports.append((current_report, list(current_batch_symbols)))
                current_report = "🧠 <b>تابع التقرير الذكي والمتقدم</b>\n" + "=" * 25 + "\n\n"
                current_batch_symbols = []
                count = 0

    if count > 0:
        reports.append((current_report, list(current_batch_symbols)))

    for rep, syms in reports:
        send_telegram_with_multiple_buttons(rep, syms)
        time.sleep(2)

def analyze_and_send_top_coin():
    best_data = get_best_market_opportunity()
    if best_data:
        report = f"🔥 <b>أفضل فرصة تداول حالياً في السوق:</b>\n\n"
        report += f"📌 <b>العملة: {best_data['symbol']}</b>\n"
        report += f"• <b>السعر الحالي:</b> ${best_data['price']:.4f}\n"
        report += f"• <b>النسبة المتوقعة:</b> <b>{best_data['win']}%</b> 🎯\n"
        report += f"• <b>الهدف الأول (TP1):</b> <b>${best_data['tp1']:.4f}</b>\n"
        report += f"• <b>الهدف الثاني (TP2):</b> <b>${best_data['tp2']:.4f}</b>\n"
        report += f"• <b>وقف الخسارة:</b> <code>${best_data['sl']:.4f}</code>\n"
        report += f"• <b>مؤشر RSI:</b> <b>{best_data['rsi']:.2f}</b>\n"
        send_telegram_single_button(report, best_data['symbol'])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوت إشارات التداول الذكي</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; text-align: center; margin: 0; }
        .container { max-width: 500px; margin: auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-top: 20px; text-align: right; border-right: 5px solid #22c55e; }
        button { background: #22c55e; color: white; border: none; padding: 14px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        button:active { background: #16a34a; }
        .loading { color: #38bdf8; margin-top: 15px; font-weight: bold; }
        .item { margin: 10px 0; font-size: 15px; }
        h2 { color: #38bdf8; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 بوت إشارات التداول الذكي</h2>
        <p>اضغط لفحص الأسواق الحية وجلب أقوى فرصة حالياً:</p>
        <button onclick="fetchSignal()">🔍 فحص السوق وجلب الصفقة</button>
        <div id="result" class="card" style="display:none;"></div>
    </div>

    <script>
        function fetchSignal() {
            const resDiv = document.getElementById('result');
            resDiv.style.display = 'block';
            resDiv.innerHTML = '<div class="loading">⏳ جاري فحص الأسواق الحية من Binance...</div>';
            
            fetch('/api/top')
            .then(response => response.json())
            .then(data => {
                if(data && data.symbol) {
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
                    resDiv.innerHTML = '<p style="color: #ef4444;">❌ لم يتم العثور على فرصة، أعد المحاولة.</p>';
                }
            }).catch(err => {
                resDiv.innerHTML = '<p style="color: #ef4444;">❌ حدث خطأ في الاتصال.</p>';
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/top', methods=['GET'])
def api_top():
    result = get_best_market_opportunity()
    return jsonify(result if result else {})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and 'message' in data:
        message = data['message']
        chat_id = str(message.get('chat', {}).get('id'))
        text = message.get('text', '').strip().lower()
        if chat_id == CHAT_ID:
            if text in ['/top', 'أفضل']:
                send_simple_message("⚡ <b>جاري البحث عن الفرصة الأقوى...</b>")
                threading.Thread(target=analyze_and_send_top_coin).start()
    return 'OK', 200

def run_scheduler():
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(analyze_and_send_signals)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
