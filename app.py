import threading
from flask import Flask, request, render_template_string, jsonify
import yfinance as yf
import pandas as pd
import requests
import time
import schedule

app = Flask('')

SYMBOLS_TO_SCAN = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "AVAX-USD", "HBAR-USD", "LINK-USD", "INJ-USD",
    "DOGE-USD", "WBTC-USD", "WBETH-USD", "ADA-USD", "NEAR-USD", "LINK-USD", "ETC-USD", "SUI-USD",
    "RENDER-USD", "FET-USD", "LTC-USD", "BCH-USD", "ZEC-USD", "TRX-USD", "DASH-USD", "APT-USD",
    "ATOM-USD", "ETC-USD", "XLM-USD", "FIL-USD", "ALGO-USD", "ICP-USD", "XAUT-USD", "EUL-USD", "ONDO-USD"
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
    <meta name="theme-color" content="#22c55e">
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
        
        /* الشريط العلوي */
        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .language-selector-container select {
            padding: 6px 12px;
            border-radius: 8px;
            background-color: #1e293b;
            color: #fff;
            border: 1px solid #475569;
            cursor: pointer;
            font-size: 14px;
            outline: none;
            width: auto;
        }

        /* شريط أزرار السوشيال ميديا تحت الوصف */
        .social-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 15px 0 20px 0;
            gap: 15px;
        }
        .social-btn {
            flex: 1;
            padding: 10px 10px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 13px;
            text-decoration: none;
            color: white;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
            transition: opacity 0.2s ease;
        }
        .social-btn:hover { opacity: 0.9; }
        .btn-facebook { background: linear-gradient(45deg, #20b0a9, #20a4b0, #137bd1, #1548bf, #1625a8); }
        .btn-instagram { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); }
        .btn-bot { background: linear-gradient(45deg, #1625a8, #1548bf, #137bd1, #20a4b0, #20b0a9); }

        .card { 
            background: rgba(30, 41, 59, 0.85); 
            backdrop-filter: blur(5px); 
            padding: 15px; 
            border-radius: 12px; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
            margin-top: 15px; 
            text-align: right; 
            border-right: 5px solid #22c55e; 
        }
        html[dir="ltr"] .card {
            text-align: left;
            border-right: none;
            border-left: 5px solid #22c55e;
        }
        .action-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        button { background: #22c55e; color: white; border: none; padding: 14px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; margin-top: 8px; }
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
        .btn-conv { background: #1F45FC; }
        
        .loading { color: #38bdf8; margin-top: 15px; font-weight: bold; font-size: 18px; }
        .item { margin: 8px 0; font-size: 14px; }
        h2 { color: #38bdf8; text-shadow: 0 2px 4px rgba(0,0,0,0.5); margin-top: 10px; }
        
        input, select {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            margin-bottom: 12px;
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid #334155;
            color: white;
            border-radius: 6px;
            box-sizing: border-box;
        }
        label { font-size: 13px; color: #38bdf8; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <!-- الشريط العلوي -->
        <div class="top-bar">
            <div class="language-selector-container">
                <select id="languageSelect" onchange="changeLanguage(this.value)">
                    <option value="ar">🇵🇸 العربية</option>
                    <option value="fr">🇫🇷 Français</option>
                    <option value="en">🇬🇧 English</option>
                </select>
            </div>
            
            <span style="color: #ef4444; font-weight: bold; font-size: 14px;">Beta version</span>
        </div>

        <h2 id="app-title">TRADING WITH KACEM 📊 🤑</h2>
        <p id="app-desc">صفقات تداول فورية (سبوت) لأكثر من 30 عملة رقمية من الأشهر والأنشط في سوق الكريبتو🔥</p>
        
        <!-- أزرار الفيسبوك وإنستغرام في الأماكن المحددة -->
        <div class="social-bar">
            <a href="https://facebook.com/dahnoun.kacem.2025" target="_blank" class="social-btn btn-facebook" id="fb-btn">
                <span>📘</span> <span id="fb-text">فايسبوك</span>
            </a>
            <a href="https://www.instagram.com/d.a__k91" target="_blank" class="social-btn btn-instagram" id="ig-btn">
                <span>📸</span> <span id="ig-text">إنستغرام</span>
            </a>
            <a href="https://t.me/Kacem991_bot" target="_blank" class="social-btn btn-bot" id="bot-btn">
                <span>🤖</span> <span id="bot-text">بوت التليجرام</span>
            </a>
        </div>

        <button onclick="fetchAllSignals()" id="btn-scan">إفحص السوق الآن 🔍</button>

        <div class="action-buttons">
            <button class="btn-custom btn-export" onclick="exportData()" id="btn-export">تصدير النتائج 💾</button>
            <button class="btn-custom btn-sort" onclick="sortSignals()" id="btn-sort">الترتيب حسب نسب النجاح 📈</button>
            <button class="btn-custom btn-top" onclick="fetchTopSignal()" id="btn-top">أفضل صفقة 🔥</button>
            <button class="btn-custom btn-conv" onclick="showCurrencyConverter()" id="btn-conv">تحويل العملات 💱</button>
        </div>

        <div id="results-container"></div>
    </div>

    <script>
        let lastMarketData = [];

        const translations = {
            ar: {
                desc: "صفقات تداول فورية (سبوت) لأكثر من 30 عملة رقمية من الأشهر والأنشط في سوق الكريبتو🔥",
                fbText: "الفيسبوك",
                igText: "إنستغرام",
                botText: "بوت التليجرام",
                scan: "إفحص السوق الآن 🔍",
                export: "تصدير النتائج 💾",
                sort: "الترتيب حسب نسب النجاح 📈",
                top: "أفضل صفقة 🔥",
                conv: "تحويل العملات 💱",
                loadingScan: "⏳ جاري فحص جميع العملات وإعداد التقارير... يرجى الانتظار",
                loadingTop: "⏳ جاري تحديد أفضل فرصة تداول...",
                loadingSort: "⏳ جاري ترتيب الصفقات حسب نسبة النجاح...",
                noData: "❌ لم يتم العثور على بيانات، أعد المحاولة.",
                errorConn: "❌ حدث خطأ في الاتصال بالسيرفر.",
                errorTop: "❌ حدث خطأ أثناء جلب أفضل صفقة.",
                errorSort: "❌ حدث خطأ أثناء الترتيب.",
                noExport: "قم بفحص السوق أولاً لتتمكن من تصدير النتائج!",
                curLabel: "تحويل العملات العالمية بسعر البنك",
                amount: "المبلغ:",
                fromCurr: "من عملة:",
                toCurr: "إلى عملة:",
                btnConvAction: "تحويل العملة",
                resTitle: "النتيجة:",
                rateLabel: "سعر الصرف:"
            },
            fr: {
                desc: "Signaux de trading spot instantanés pour plus de 30 cryptomonnaies populaires🔥",
                fbText: "Facebook",
                igText: "Instagram",
                botText: "Bot Telegram",
                scan: "Scanner le marché 🔍",
                export: "Exporter les résultats 💾",
                sort: "Trier par taux de réussite 📈",
                top: "Meilleur trade 🔥",
                conv: "Convertisseur 💱",
                loadingScan: "⏳ Analyse de toutes les cryptos en cours... Veuillez patienter",
                loadingTop: "⏳ Recherche de la meilleure opportunité...",
                loadingSort: "⏳ Tri des signaux par taux de réussite...",
                noData: "❌ Aucune donnée trouvée, réessayez.",
                errorConn: "❌ Erreur de connexion au serveur.",
                errorTop: "❌ Erreur lors de la récupération du meilleur trade.",
                errorSort: "❌ Erreur lors du tri.",
                noExport: "Veuillez d'abord scanner le marché pour exporter !",
                curLabel: "Convertisseur de devises au taux bancaire",
                amount: "Montant:",
                fromCurr: "De la devise:",
                toCurr: "Vers la devise:",
                btnConvAction: "Convertir",
                resTitle: "Résultat:",
                rateLabel: "Taux de change:"
            },
            en: {
                desc: "Instant spot trading signals for over 30 popular cryptocurrencies🔥",
                fbText: "Facebook",
                igText: "Instagram",
                botText: "Telegram Bot",
                scan: "Scan Market Now 🔍",
                export: "Export Results 💾",
                sort: "Sort by Success Rate 📈",
                top: "Top Signal 🔥",
                conv: "Currency Converter 💱",
                loadingScan: "⏳ Scanning all coins and preparing reports... Please wait",
                loadingTop: "⏳ Identifying the best trading opportunity...",
                loadingSort: "⏳ Sorting signals by success rate...",
                noData: "❌ No data found, please try again.",
                errorConn: "❌ Server connection error.",
                errorTop: "❌ Error fetching top signal.",
                errorSort: "❌ Error while sorting.",
                noExport: "Please scan the market first to export results!",
                curLabel: "Global Currency Converter at Bank Rate",
                amount: "Amount:",
                fromCurr: "From Currency:",
                toCurr: "To Currency:",
                btnConvAction: "Convert Currency",
                resTitle: "Result:",
                rateLabel: "Exchange Rate:"
            }
        };

        function changeLanguage(lang) {
            const htmlTag = document.documentElement;
            if (lang === 'ar') {
                htmlTag.setAttribute('dir', 'rtl');
                htmlTag.setAttribute('lang', 'ar');
            } else {
                htmlTag.setAttribute('dir', 'ltr');
                htmlTag.setAttribute('lang', lang);
            }

            const t = translations[lang];
            document.getElementById('app-desc').innerText = t.desc;
            document.getElementById('fb-text').innerText = t.fbText;
            document.getElementById('ig-text').innerText = t.igText;
            document.getElementById('bot-text').innerText = t.botText;
            document.getElementById('btn-scan').innerText = t.scan;
            document.getElementById('btn-export').innerText = t.export;
            document.getElementById('btn-sort').innerText = t.sort;
            document.getElementById('btn-top').innerText = t.top;
            document.getElementById('btn-conv').innerText = t.conv;
        }

        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
            .then(() => console.log('Service Worker Registered'))
            .catch((err) => console.log('Service Worker Failed', err));
        }

        function getCurrentLang() {
            return document.documentElement.getAttribute('lang') || 'ar';
        }

        function fetchAllSignals() {
            const lang = getCurrentLang();
            const t = translations[lang];
            const container = document.getElementById('results-container');
            container.innerHTML = `<div class="loading">${t.loadingScan}</div>`;
            
            fetch('/api/all')
            .then(response => response.json())
            .then(data => {
                lastMarketData = data;
                renderCards(data, container, lang);
            }).catch(err => {
                container.innerHTML = `<p style="color: #ef4444; margin-top:20px;">${t.errorConn}</p>`;
            });
        }

        function renderCards(data, container, lang) {
            const t = translations[lang];
            if(data && data.length > 0) {
                let html = '';
                data.forEach(res => {
                    const symbolText = lang === 'ar' ? '📌 العملة:' : (lang === 'fr' ? '📌 Symbole:' : '📌 Symbol:');
                    const priceText = lang === 'ar' ? '💵 السعر الحالي:' : (lang === 'fr' ? '💵 Prix actuel:' : '💵 Current Price:');
                    const winText = lang === 'ar' ? '🎯 نسبة النجاح المتوقعة:' : (lang === 'fr' ? '🎯 Taux de réussite:' : '🎯 Expected Win Rate:');
                    const tp1Text = lang === 'ar' ? '☝ الهدف الأول (TP1):' : (lang === 'fr' ? '☝ 1er Objectif (TP1):' : '☝ 1st Target (TP1):');
                    const tp2Text = lang === 'ar' ? '✌ الهدف الثاني (TP2):' : (lang === 'fr' ? '✌ 2ème Objectif (TP2):' : '✌ 2nd Target (TP2):');
                    const slText = lang === 'ar' ? '🛑 وقف الخسارة (SL):' : (lang === 'fr' ? '🛑 Stop Loss (SL):' : '🛑 Stop Loss (SL):');
                    const rsiText = lang === 'ar' ? '📊 مؤشر RSI:' : (lang === 'fr' ? '📊 Indicateur RSI:' : '📊 RSI Indicator:');
                    const condText = lang === 'ar' ? '🔍 الشروط المتقدمة: RSI' : (lang === 'fr' ? '🔍 Conditions: RSI' : '🔍 Advanced Conditions: RSI');
                    const trendText = lang === 'ar' ? 'الاتجاه' : (lang === 'fr' ? 'Tendance' : 'Trend');
                    const liqText = lang === 'ar' ? 'السيولة' : (lang === 'fr' ? 'Liquidité' : 'Liquidity');

                    html += `
                        <div class="card">
                            <h3 style="color: #64DD17; margin-top:0;">${symbolText} ${res.symbol}</h3>
                            <div class="item"><b>${priceText}</b> $${res.price.toFixed(4)}</div>
                            <div class="item"><b>${winText}</b> ${res.win}%</div>
                            <div class="item" style="color: #38bdf8;"><b>${tp1Text}</b> $${res.tp1.toFixed(4)}</div>
                            <div class="item" style="color: #38bdf8;"><b>${tp2Text}</b> $${res.tp2.toFixed(4)}</div>
                            <div class="item" style="color: #ef4444;"><b>${slText}</b> $${res.sl.toFixed(4)}</div>
                            <div class="item"><b>${rsiText}</b> ${res.rsi.toFixed(2)}</div>
                            <div class="item"><b>${condText}</b> ${res.r_icon} | ${trendText} ${res.t_icon} | ${liqText} ${res.v_icon}</div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            } else {
                container.innerHTML = `<p style="color: #ef4444; margin-top:20px;">${t.noData}</p>`;
            }
        }

        function fetchTopSignal() {
            const lang = getCurrentLang();
            const t = translations[lang];
            const container = document.getElementById('results-container');
            container.innerHTML = `<div class="loading">${t.loadingTop}</div>`;
            
            fetch('/api/top')
            .then(res => res.json())
            .then(best => {
                if(best && best.symbol) {
                    const topTitle = lang === 'ar' ? `🔥 أفضل فرصة تداول حالياً: ${best.symbol}` : (lang === 'fr' ? `🔥 Meilleure opportunité actuelle : ${best.symbol}` : `🔥 Best current trading opportunity: ${best.symbol}`);
                    const priceText = lang === 'ar' ? '💵 السعر الحالي:' : (lang === 'fr' ? '💵 Prix actuel:' : '💵 Current Price:');
                    const winText = lang === 'ar' ? '🎯 نسبة النجاح المتوقعة:' : (lang === 'fr' ? '🎯 Taux de réussite:' : '🎯 Expected Win Rate:');
                    const tp1Text = lang === 'ar' ? '☝ الهدف الأول (TP1):' : (lang === 'fr' ? '☝ 1er Objectif (TP1):' : '☝ 1st Target (TP1):');
                    const tp2Text = lang === 'ar' ? '✌ الهدف الثاني (TP2):' : (lang === 'fr' ? '✌ 2ème Objectif (TP2):' : '✌ 2nd Target (TP2):');
                    const slText = lang === 'ar' ? '🛑 وقف الخسارة (SL):' : (lang === 'fr' ? '🛑 Stop Loss (SL):' : '🛑 Stop Loss (SL):');

                    container.innerHTML = `
                        <div class="card" style="border-right-color: #f59e0b;">
                            <h3 style="color: #f59e0b; margin-top:0;">${topTitle}</h3>
                            <div class="item"><b>${priceText}</b> $${best.price.toFixed(4)}</div>
                            <div class="item"><b>${winText}</b> ${best.win}%</div>
                            <div class="item" style="color: #38bdf8;"><b>${tp1Text}</b> $${best.tp1.toFixed(4)}</div>
                            <div class="item" style="color: #38bdf8;"><b>${tp2Text}</b> $${best.tp2.toFixed(4)}</div>
                            <div class="item" style="color: #ef4444;"><b>${slText}</b> $${best.sl.toFixed(4)}</div>
                        </div>
                    `;
                } else {
                    container.innerHTML = `<p style="color: #ef4444; margin-top:20px;">${t.noData}</p>`;
                }
            }).catch(err => {
                container.innerHTML = `<p style="color: #ef4444; margin-top:20px;">${t.errorTop}</p>`;
            });
        }

        function sortSignals() {
            const lang = getCurrentLang();
            const t = translations[lang];
            const container = document.getElementById('results-container');
            container.innerHTML = `<div class="loading">${t.loadingSort}</div>`;
            
            fetch('/api/sort')
            .then(res => res.json())
            .then(data => {
                lastMarketData = data;
                renderCards(data, container, lang);
            }).catch(err => {
                container.innerHTML = `<p style="color: #ef4444; margin-top:20px;">${t.errorSort}</p>`;
            });
        }

        function exportData() {
            const lang = getCurrentLang();
            const t = translations[lang];
            if (lastMarketData.length === 0) {
                alert(t.noExport);
                return;
            }
            let textContent = "--- Trading Signals Report ---\\n\\n";
            lastMarketData.forEach(res => {
                textContent += `Symbol: ${res.symbol}\\nPrice: ${res.price}\\nWin Rate: ${res.win}%\\nTP1: ${res.tp1}\\nTP2: ${res.tp2}\\nSL: ${res.sl}\\n-------------------\\n`;
            });
            let blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
            let url = URL.createObjectURL(blob);
            let a = document.createElement('a');
            a.href = url;
            a.download = 'Trading_Report.txt';
            a.click();
        }

        function showCurrencyConverter() {
            const lang = getCurrentLang();
            const t = translations[lang];
            const container = document.getElementById('results-container');
            container.innerHTML = `
                <div class="card" style="border-right-color: #10b981;">
                    <h3 style="color: #10b981; margin-top:0;">💱 ${t.curLabel}</h3>
                    <label>${t.amount}</label>
                    <input type="number" id="conv-amount" value="100">
                    
                    <label>${t.fromCurr}</label>
                    <select id="conv-from">
                        <option value="USD" selected>USD - US Dollar</option>
                        <option value="EUR">EUR - Euro</option>
                        <option value="GBP">GBP - British Pound</option>
                        <option value="SAR">SAR - Saudi Riyal</option>
                        <option value="AED">AED - UAE Dirham</option>
                        <option value="EGP">EGP - Egyptian Pound</option>
                        <option value="DZD">DZD - Algerian Dinar</option>
                        <option value="MAD">MAD - Moroccan Dirham</option>
                        <option value="JOD">JOD - Jordanian Dinar</option>
                        <option value="KWD">KWD - Kuwaiti Dinar</option>
                    </select>
                    
                    <label>${t.toCurr}</label>
                    <select id="conv-to">
                        <option value="USD">USD - US Dollar</option>
                        <option value="EUR" selected>EUR - Euro</option>
                        <option value="GBP">GBP - British Pound</option>
                        <option value="SAR">SAR - Saudi Riyal</option>
                        <option value="AED">AED - UAE Dirham</option>
                        <option value="EGP">EGP - Egyptian Pound</option>
                        <option value="DZD">DZD - Algerian Dinar</option>
                        <option value="MAD">MAD - Moroccan Dirham</option>
                        <option value="JOD">JOD - Jordanian Dinar</option>
                        <option value="KWD">KWD - Kuwaiti Dinar</option>
                    </select>
                    
                    <button onclick="convertCurrency()" style="background:#10b981; margin-top:5px;">${t.btnConvAction}</button>
                    <div id="conv-result" style="margin-top: 15px;"></div>
                </div>
            `;
        }

        function convertCurrency() {
            const lang = getCurrentLang();
            const amount = parseFloat(document.getElementById('conv-amount').value);
            const from = document.getElementById('conv-from').value;
            const to = document.getElementById('conv-to').value;
            const resDiv = document.getElementById('conv-result');

            if (!amount) {
                resDiv.innerHTML = '<p style="color: #ef4444;">❌ Invalid amount.</p>';
                return;
            }

            resDiv.innerHTML = '<div style="color: #38bdf8;">⏳ Fetching exchange rates...</div>';

            fetch(`/api/convert?from=${from}&to=${to}&amount=${amount}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const t = translations[getCurrentLang()];
                    resDiv.innerHTML = `
                        <hr style="border-color: #334155;">
                        <div class="item" style="font-size: 16px; color: #64DD17;"><b>${t.resTitle}</b> ${data.result.toFixed(4)} ${to}</div>
                        <div class="item" style="font-size: 12px; color: #94a3b8;">${t.rateLabel} 1 ${from} = ${data.rate.toFixed(4)} ${to}</div>
                    `;
                } else {
                    resDiv.innerHTML = '<p style="color: #ef4444;">❌ Failed to fetch rates.</p>';
                }
            }).catch(err => {
                resDiv.innerHTML = '<p style="color: #ef4444;">❌ Connection error.</p>';
            });
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
        "theme_color": "#33779c",
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

@app.route('/api/convert', methods=['GET'])
def api_convert():
    from_curr = request.args.get('from', 'USD').upper()
    to_curr = request.args.get('to', 'EUR').upper()
    try:
        amount = float(request.args.get('amount', 1))
    except ValueError:
        amount = 1.0

    try:
        pair = f"{from_curr}{to_curr}=X"
        ticker = yf.Ticker(pair)
        hist = ticker.history(period="1d", interval="1m")
        
        if not hist.empty:
            rate = float(hist['Close'].iloc[-1])
        else:
            pair_inv = f"{to_curr}{from_curr}=X"
            ticker_inv = yf.Ticker(pair_inv)
            hist_inv = ticker_inv.history(period="1d", interval="1m")
            if not hist_inv.empty:
                rate = 1.0 / float(hist_inv['Close'].iloc[-1])
            else:
                rate = 1.0

        result = amount * rate
        return jsonify({
            "success": True,
            "rate": float(rate),
            "result": float(result)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def run_http():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_http).start()
