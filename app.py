import threading
from flask import Flask, request, render_template_string, jsonify
import yfinance as yf
import pandas as pd
import requests
import time
import schedule

app = Flask('')

TELEGRAM_TOKEN = "8968850415:AAG9DwLeyHQ7iNuLmISdhnHnSh7m6us_PgQ"
CHAT_ID = "5723285644"

SYMBOLS_TO_SCAN = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "DOGE-USD", "AVAX-USD", "LINK-USD", "ADA-USD", "NEAR-USD",
    "RENDER-USD", "FET-USD", "LTC-USD", "BCH-USD", "BTC-USD",
    "ATOM-USD", "ETC-USD", "XLM-USD", "FIL-USD", "ALGO-USD", "ICP-USD"
]
CHECK_INTERVAL_HOURS = 4

def send_telegram_with_multiple_buttons(text, symbols_list):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard_buttons = []
    for sym in symbols_list:
        binance_url_format = sym.replace('USDT', '_USDT')
        button_row = [{"text": f"🟡 بايننس {sym}", "url": f"https://www.binance.com/en/trade/{binance_url_format}"}]
        keyboard_buttons.append(button_row)
    
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": keyboard_buttons}
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"⚠️ خطأ في إرسال التيليجرام: {e}")

def send_telegram_single_button(text, symbol):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    binance_url_format = symbol.replace('USDT', '_USDT')
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[{"text": f"🟡 بايننس {symbol}", "url": f"https://www.binance.com/en/trade/{binance_url_format}"}]]}
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ خطأ في إرسال الرسالة: {e}")

def send_simple_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ خطأ: {e}")

def get_all_market_opportunities():
    all_results = []
    for ticker in SYMBOLS_TO_SCAN:
        symbol = ticker.replace("-USD", "USDT")
        try:
            data = yf.Ticker(ticker).history(period="250d", interval="1d")
            if data.empty or len(data) < 30:
                continue

            df = data.copy()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            data_len = len(df)
            span_val = 50 if data_len >= 50 else data_len
            ema200_span = 200 if data_len >= 200 else span_val

            df['EMA50'] = df['Close'].ewm(span=span_val, adjust=False).mean()
            df['EMA200'] = df['Close'].ewm(span=ema200_span, adjust=False).mean()
            df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()

            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['ATR'] = true_range.rolling(14).mean()

            current_price = df['Close'].iloc[-1]
            last_rsi = df['RSI'].iloc[-1]
            last_ema50 = df['EMA50'].iloc[-1]
            last_ema200 = df['EMA200'].iloc[-1]
            last_volume = df['Volume'].iloc[-1]
            avg_volume = df['Vol_SMA20'].iloc[-1]
            if pd.isna(avg_volume) or avg_volume <= 0:
                avg_volume = last_volume

            last_atr = df['ATR'].iloc[-1]
            if pd.isna(last_atr) or last_atr <= 0:
                last_atr = current_price * 0.03

            rsi_condition = last_rsi < 55
            trend_condition = (current_price > last_ema200) and (last_ema50 > last_ema200)
            volume_condition = last_volume > (avg_volume * 0.8)

            r_icon = "✅" if rsi_condition else "❌"
            t_icon = "✅" if trend_condition else "❌"
            v_icon = "✅" if volume_condition else "❌"

            trend_strength_pct = ((current_price - last_ema200) / last_ema200) * 100
            trend_score = min(max(trend_strength_pct * 3, 0), 30)

            rsi_score = 25
            if 40 <= last_rsi <= 60:
                rsi_score = 25
            elif last_rsi < 40:
                rsi_score = 20
            else:
                rsi_score = max(25 - (last_rsi - 60), 5)

            volume_ratio = last_volume / avg_volume if avg_volume > 0 else 1.0
            volume_score = min(volume_ratio * 15, 30)

            calculated_win_rate = 30 + trend_score + rsi_score + volume_score
            win_probability = round(min(max(calculated_win_rate, 45), 96), 1)

            dynamic_sl = current_price - (1.5 * last_atr)
            tp1 = current_price + (2 * last_atr)
            tp2 = current_price + (3.5 * last_atr)
            if dynamic_sl >= current_price:
                dynamic_sl = current_price * 0.97

            all_results.append({
                "symbol": symbol,
                "price": current_price,
                "win": win_probability,
                "tp1": tp1,
                "tp2": tp2,
                "sl": dynamic_sl,
                "rsi": last_rsi,
                "r_icon": r_icon,
                "t_icon": t_icon,
                "v_icon": v_icon
            })
        except Exception as e:
            continue
    return all_results

def analyze_and_send_signals():
    reports = []
    current_report = f"🧠 <b>التقرير الذكي والمتقدم للعملات (أجزاء)</b>\n" + "=" * 25 + "\n\n"
    current_batch_symbols = []
    count = 0

    results = get_all_market_opportunities()
    for res in results:
        current_report += f"📌 <b><code style='color:#64DD17;'>العملة: {res['symbol']}</code></b>\n"
        current_report += f"• <b>السعر الحالي:</b> ${res['price']:.4f}\n"
        current_report += f"• <b>النسبة المتوقعة لنجاح الصفقة:</b> <b>{res['win']}%</b> 🎯\n"
        current_report += f"• <b>الهدف الديناميكي (TP1):</b> <b>${res['tp1']:.4f}</b>\n"
        current_report += f"• <b>الهدف البعيد (TP2):</b> <b>${res['tp2']:.4f}</b>\n"
        current_report += f"• <b>وقف الخسارة الذكي (ATR SL):</b> <code>${res['sl']:.4f}</code>\n"
        current_report += f"• <b>مؤشر RSI:</b> <b>{res['rsi']:.2f}</b>\n"
        current_report += f"🔍 <b>الشروط المتقدمة:</b> RSI {res['r_icon']} | الاتجاه الذكي {res['t_icon']} | السيولة {res['v_icon']}\n"
        current_report += "-" * 25 + "\n\n"

        current_batch_symbols.append(res['symbol'])
        count += 1
        if count == 5:
            reports.append((current_report, list(current_batch_symbols)))
            current_report = f"🧠 <b>تابع التقرير الذكي والمتقدم للعملات</b>\n" + "=" * 25 + "\n\n"
            current_batch_symbols = []
            count = 0

    if count > 0:
        reports.append((current_report, list(current_batch_symbols)))

    for rep, syms in reports:
        send_telegram_with_multiple_buttons(rep, syms)
        time.sleep(2)

def analyze_and_send_top_coin():
    results = get_all_market_opportunities()
    if not results:
        send_simple_message("❌ لم يتم العثور على فرصة مناسبة حالياً.")
        return
    best_data = max(results, key=lambda x: x['win'])

    report = f"🔥 <b>أفضل فرصة تداول حالياً في السوق:</b>\n\n"
    report += f"📌 <b><code style='color:#64DD17;'>العملة: {best_data['symbol']}</code></b>\n"
    report += f"• <b>السعر الحالي:</b> ${best_data['price']:.4f}\n"
    report += f"• <b>النسبة المتوقعة لنجاح الصفقة:</b> <b>{best_data['win']}%</b> 🎯\n"
    report += f"• <b>الهدف الديناميكي (TP1):</b> <b>${best_data['tp1']:.4f}</b>\n"
    report += f"• <b>الهدف البعيد (TP2):</b> <b>${best_data['tp2']:.4f}</b>\n"
    report += f"• <b>وقف الخسارة الذكي:</b> <code>${best_data['sl']:.4f}</code>\n"
    report += f"• <b>مؤشر RSI:</b> <b>{best_data['rsi']:.2f}</b>\n"
    
    send_telegram_single_button(report, best_data['symbol'])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوت إشارات التداول الذكي - جميع العملات</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; text-align: center; margin: 0; }
        .container { max-width: 700px; margin: auto; }
        .card { background: #1e293b; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-top: 15px; text-align: right; border-right: 5px solid #22c55e; }
        button { background: #22c55e; color: white; border: none; padding: 14px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        button:active { background: #16a34a; }
        .loading { color: #38bdf8; margin-top: 15px; font-weight: bold; font-size: 18px; }
        .item { margin: 8px 0; font-size: 14px; }
        h2 { color: #38bdf8; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 TRADING WITH KACEM</h2>
        <p>اضغط لفحص كافة الأسواق الحية وجلب تقارير العملات كاملة:</p>
        <button onclick="fetchAllSignals()">🔍 افحص السوق الآن</button>
        <div id="results-container"></div>
    </div>

    <script>
        function fetchAllSignals() {
            const container = document.getElementById('results-container');
            container.innerHTML = '<div class="loading">⏳ جاري فحص جميع العملات وإعداد التقارير... يرجى الانتظار</div>';
            
            fetch('/api/all')
            .then(response => response.json())
            .then(data => {
                if(data && data.length > 0) {
                    let html = '';
                    data.forEach(res => {
                        html += `
                            <div class="card">
                                <h3 style="color: #64DD17; margin-top:0;">📌 العملة: ${res.symbol}</h3>
                                <div class="item">💵 <b>السعر الحالي:</b> $${res.price.toFixed(4)}</div>
                                <div class="item">🎯 <b>نسبة النجاح المتوقعة:</b> ${res.win}%</div>
                                <div class="item" style="color: #38bdf8;">📈 <b>الهدف الأول (TP1):</b> $${res.tp1.toFixed(4)}</div>
                                <div class="item" style="color: #38bdf8;">🚀 <b>الهدف الثاني (TP2):</b> $${res.tp2.toFixed(4)}</div>
                                <div class="item" style="color: #ef4444;">🛑 <b>وقف الخسارة (SL):</b> $${res.sl.toFixed(4)}</div>
                                <div class="item">📊 <b>مؤشر RSI:</b> ${res.rsi.toFixed(2)}</div>
                                <div class="item">🔍 <b>الشروط المتقدمة:</b> RSI ${res.r_icon} | الاتجاه ${res.t_icon} | السيولة ${res.v_icon}</div>
                            </div>
                        `;
                    });
                    container.innerHTML = html;
                } else {
                    container.innerHTML = '<p style="color: #ef4444; margin-top:20px;">❌ لم يتم العثور على بيانات، أعد المحاولة.</p>';
                }
            }).catch(err => {
                container.innerHTML = '<p style="color: #ef4444; margin-top:20px;">❌ حدث خطأ في الاتصال بالسيرفر.</p>';
            });
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        data = request.get_json()
        if data and 'message' in data:
            message = data['message']
            chat_id = str(message.get('chat', {}).get('id'))
            text = message.get('text', '').strip().lower()
            
            if chat_id == CHAT_ID:
                if text == '/update' or text == 'تحديث':
                    send_simple_message("🔄 <b>تم استلام طلبك! جاري فحص السوق وإرسال التقارير فوراً...</b>")
                    threading.Thread(target=analyze_and_send_signals).start()
                elif text == '/top' or text == 'أفضل':
                    send_simple_message("⚡ <b>جاري البحث في جميع العملات عن الفرصة الأقوى حالياً...</b>")
                    threading.Thread(target=analyze_and_send_top_coin).start()
                elif text in ['clear', 'مسح', '/clear']:
                    send_simple_message("🧹 <b>تم مسح الذاكرة المؤقتة وإعادة تعيين حالة البوت بنجاح!</b>")
                elif text == '/status' or text == 'حالة':
                    send_simple_message("🟢 <b>البوت يعمل بكفاءة تامة ومتصل بالسيرفر بنجاح!</b>")
                elif text == '/list' or text == 'عملات':
                    symbols_str = ", ".join([s.replace("-USD", "") for s in SYMBOLS_TO_SCAN])
                    send_simple_message(f"📋 <b>العملات التي يتم مراقبتها حالياً:</b>\n{symbols_str}")
                elif text == '/help' or text == 'مساعدة':
                    help_text = (
                        "🤖 <b>قائمة أوامر البوت الذكي:</b>\n\n"
                        "• <b>/update</b> أو <b>تحديث</b>: لفحص السوق وإرسال التقارير كاملة.\n"
                        "• <b>/top</b> أو <b>أفضل</b>: لعرض أفضل عملة ذات أعلى نسبة نجاح حالياً.\n"
                        "• <b>/clear</b> أو <b>مسح</b>: لمسح الذاكرة المؤقتة وإعادة الضبط.\n"
                        "• <b>/status</b> أو <b>حالة</b>: للتأكد من عمل البوت.\n"
                        "• <b>/list</b> أو <b>عملات</b>: لعرض العملات المراقبة.\n"
                        "• <b>/help</b> أو <b>مساعدة</b>: لعرض هذه القائمة."
                    )
                    send_simple_message(help_text)
                else:
                    send_simple_message("❓ أمر غير معروف. أرسل <b>/help</b> لعرض الأوامر المتاحة.")
            return 'OK', 200
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/all', methods=['GET'])
def api_all():
    return jsonify(get_all_market_opportunities())

def run_http():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_http).start()
schedule.every(CHECK_INTERVAL_HOURS).hours.do(analyze_and_send_signals)

while True:
    schedule.run_pending()
    time.sleep(1)
