import threading
from flask import Flask, request, render_template_string, jsonify
import yfinance as yf
import pandas as pd
import requests
import time
import schedule

app = Flask('')

SYMBOLS_TO_SCAN = [
    "ZEC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "DOGE-USD", "AVAX-USD", "LINK-USD", "ADA-USD", "NEAR-USD",
    "RENDER-USD", "FET-USD", "LTC-USD", "BCH-USD", "BTC-USD",
    "ATOM-USD", "ETC-USD", "XLM-USD", "FIL-USD", "ALGO-USD", "ICP-USD"
]

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
                "price": float(current_price),
                "win": float(win_probability),
                "tp1": float(tp1),
                "tp2": float(tp2),
                "sl": float(dynamic_sl),
                "rsi": float(last_rsi),
                "r_icon": r_icon,
                "t_icon": t_icon,
                "v_icon": v_icon
            })
        except Exception as e:
            continue
    return all_results

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TRADING WITH KACEM</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#33779c">
    <style>
        body { 
            font-family: Tahoma, sans-serif; 
            background: linear-gradient(rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.85)), 
                url('https://res.cloudinary.com/ke7jwn4a/image/upload/v1785554014/copy_of_22222222222222222222222_fcin7r.png') no-repeat center center fixed; 
            background-size: cover;
            color: #f8fafc; 
            padding: 20px; 
            text-align: center; 
            margin: 0; 
        }
        .container { max-width: 700px; margin: auto; }
        .card { 
            background: rgba(30, 41, 59, 0.85); 
            backdrop-filter: blur(5px); 
            padding: 15px; 
            border-radius: 12px; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
            margin-top: 15px; 
            text-align: right; 
            border-right: 5px solid #33779c; 
        }
        .action-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        button { background: #33779c; color: white; border: none; padding: 14px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; margin-top: 8px; }
        .btn-custom { 
            flex: 1; 
            min-width: 140px; 
            padding: 14px 10px; 
            font-size: 15px; 
            font-weight: bold; 
            border-radius: 8px; 
            border: none; 
            cursor: pointer; 
            color: white; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: transform 0.1s ease;
        }
        .btn-custom:active { transform: scale(0.97); }
        .btn-top { background: #f59e0b; }
        .btn-sort { background: #8b5cf6; }
        .btn-export { background: #ec4899; }
        
        .loading { color: #38bdf8; margin-top: 15px; font-weight: bold; font-size: 18px; }
        .item { margin: 8px 0; font-size: 14px; }
        h2 { color: #38bdf8; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 TRADING WITH KACEM</h2>
        <p>اضغط لفحص كافة الأسواق الحية وجلب تقارير العملات كاملة:</p>
        
        <button onclick="fetchAllSignals()">🔍 إفحص السوق الآن</button>

        <div class="action-buttons">
            <button class="btn-custom btn-export" onclick="exportData()">تصدير النتائج 💾</button>
            <button class="btn-custom btn-sort" onclick="sortSignals()">الترتيب حسب نسب النجاح 📈</button>
            <button class="btn-custom btn-top" onclick="fetchTopSignal()">أفضل صفقة 🔥</button>
        </div>

        <div id="results-container"></div>
    </div>

    <script>
        let lastMarketData = [];

        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
            .then(() => console.log('Service Worker Registered'))
            .catch((err) => console.log('Service Worker Failed', err));
        }

        function fetchAllSignals() {
            const container = document.getElementById('results-container');
            container.innerHTML = '<div class="loading">⏳ جاري فحص جميع العملات وإعداد التقارير... يرجى الانتظار</div>';
            
            fetch('/api/all')
            .then(response => response.json())
            .then(data => {
                lastMarketData = data;
                renderCards(data, container);
            }).catch(err => {
                container.innerHTML = '<p style="color: #ef4444; margin-top:20px;">❌ حدث خطأ في الاتصال بالسيرفر.</p>';
            });
        }

        function renderCards(data, container) {
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
        }

        function fetchTopSignal() {
            const container = document.getElementById('results-container');
            container.innerHTML = '<div class="loading">⏳ جاري تحديد أفضل فرصة تداول...</div>';
            
            fetch('/api/top')
            .then(res => res.json())
            .then(best => {
                if(best && best.symbol) {
                    container.innerHTML = `
                        <div class="card" style="border-right-color: #f59e0b;">
                            <h3 style="color: #f59e0b; margin-top:0;">🔥 أفضل فرصة تداول حالياً: ${best.symbol}</h3>
                            <div class="item">💵 <b>السعر الحالي:</b> $${best.price.toFixed(4)}</div>
                            <div class="item">🎯 <b>نسبة النجاح المتوقعة:</b> ${best.win}%</div>
                            <div class="item" style="color: #38bdf8;">📈 <b>الهدف الأول (TP1):</b> $${best.tp1.toFixed(4)}</div>
                            <div class="item" style="color: #38bdf8;">🚀 <b>الهدف الثاني (TP2):</b> $${best.tp2.toFixed(4)}</div>
                            <div class="item" style="color: #ef4444;">🛑 <b>وقف الخسارة (SL):</b> $${best.sl.toFixed(4)}</div>
                        </div>
                    `;
                } else {
                    container.innerHTML = '<p style="color: #ef4444; margin-top:20px;">❌ لا توجد بيانات متاحة حالياً.</p>';
                }
            }).catch(err => {
                container.innerHTML = '<p style="color: #ef4444; margin-top:20px;">❌ حدث خطأ أثناء جلب أفضل صفقة.</p>';
            });
        }

        function sortSignals() {
            const container = document.getElementById('results-container');
            container.innerHTML = '<div class="loading">⏳ جاري ترتيب الصفقات حسب نسبة النجاح...</div>';
            
            fetch('/api/sort')
            .then(res => res.json())
            .then(data => {
                lastMarketData = data;
                renderCards(data, container);
            }).catch(err => {
                container.innerHTML = '<p style="color: #ef4444; margin-top:20px;">❌ حدث خطأ أثناء الترتيب.</p>';
            });
        }

        function exportData() {
            if (lastMarketData.length === 0) {
                alert('قم بفحص السوق أولاً لتتمكن من تصدير النتائج!');
                return;
            }
            let textContent = "--- تقرير إشارات التداول الذكي ---\\n\\n";
            lastMarketData.forEach(res => {
                textContent += `العملة: ${res.symbol}\\nالسعر: ${res.price}\\nنسبة النجاح: ${res.win}%\\nالهدف الأول: ${res.tp1}\\nالهدف الثاني: ${res.tp2}\\nوقف الخسارة: ${res.sl}\\n-------------------\\n`;
            });
            let blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
            let url = URL.createObjectURL(blob);
            let a = document.createElement('a');
            a.href = url;
            a.download = 'Trading_Report.txt';
            a.click();
        }
    </script>
</body>
</html>
"""

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "id": "/",
        "name": "TRADING WITH KACEM",
        "short_name": "TRADING WITH KACEM",
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0f172a",
        "theme_color": "#22c55e",
        "description": "بوت فحص الأسواق وجلب فرص التداول الذكية بدقة عالية.",
        "categories": ["finance", "business", "productivity"],
        "icons": [
            {
                "src": "https://res.cloudinary.com/ke7jwn4a/image/upload/v1785554014/copy_of_22222222222222222222222_fcin7r.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "screenshots": [
            {
                "src": "https://res.cloudinary.com/ke7jwn4a/image/upload/v1785554014/copy_of_22222222222222222222222_fcin7r.png",
                "sizes": "512x512",
                "type": "image/png",
                "form_factor": "wide",
                "label": "لقطة شاشة لتطبيق إشارات التداول"
            }
        ]
    }
    return jsonify(manifest_data)

@app.route('/sw.js')
def service_worker():
    sw_code = """
    const CACHE_NAME = 'trading-kacem-v1';
    const urlsToCache = [
        '/',
        '/manifest.json'
    ];

    self.addEventListener('install', (e) => {
        e.waitUntil(
            caches.open(CACHE_NAME)
                .then((cache) => cache.addAll(urlsToCache))
        );
    });

    self.addEventListener('fetch', (e) => {
        e.respondWith(
            caches.match(e.request)
                .then((response) => response || fetch(e.request))
        );
    });
    """
    return sw_code, 200, {'Content-Type': 'application/javascript'}

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/all', methods=['GET'])
def api_all():
    return jsonify(get_all_market_opportunities())

@app.route('/api/top', methods=['GET'])
def api_top():
    results = get_all_market_opportunities()
    if not results:
        return jsonify({})
    best = max(results, key=lambda x: x['win'])
    return jsonify(best)

@app.route('/api/sort', methods=['GET'])
def api_sort():
    results = get_all_market_opportunities()
    results.sort(key=lambda x: x['win'], reverse=True)
    return jsonify(results)

def run_http():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_http).start()
