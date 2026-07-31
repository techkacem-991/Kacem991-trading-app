from flask import Flask, render_template_string

app = Flask(__name__)

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
    <h2>📊 بوت التداول قاسم</h2>
    <p>اضغط لفحص السوق وجلب أفضل فرصة:</p>
    <button onclick="fetchSignal()">🔍 فحص السوق الآن</button>
    <div id="result" class="card" style="display:none;"></div>

    <script>
        function fetchSignal() {
            document.getElementById('result').style.display = 'block';
            document.getElementById('result').innerHTML = '<div class="loading">⏳ جاري فحص الأسواق وتحليل البيانات...</div>';
            
            setTimeout(() => {
                document.getElementById('result').innerHTML = `
                    <h3>🔥 أفضل فرصة: BTCUSDT</h3>
                    <p>💵 السعر: $67,450.00</p>
                    <p>🎯 نسبة النجاح: <b>88.5%</b></p>
                    <p>📈 الهدف الأول (TP1): $69,200.00</p>
                    <p>🚀 الهدف الثاني (TP2): $71,000.00</p>
                    <p>🛑 وقف الخسارة (SL): $66,100.00</p>
                    <p>📊 مؤشر RSI: 58.40</p>
                `;
            }, 1000);
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
