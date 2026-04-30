from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # للسماح بالطلبات من أي نطاق

# ============================================
# الصفحة الرئيسية
# ============================================
@app.route('/')
def home():
    return jsonify({
        "status": "ok",
        "service": "الخدمة الجديدة - مروم FM",
        "time": datetime.now().isoformat(),
        "endpoints": [
            "/",
            "/health",
            "/api/info",
            "/api/echo",
            "/api/time"
        ]
    })

# ============================================
# مسار الصحة (للمراقبة)
# ============================================
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "new-service",
        "timestamp": datetime.now().isoformat()
    }), 200

# ============================================
# معلومات عن الخدمة
# ============================================
@app.route('/api/info')
def info():
    return jsonify({
        "service": "الخدمة الجديدة - مروم FM",
        "version": "1.0.0",
        "python_version": "3.11",
        "server": os.environ.get('RENDER_SERVICE_NAME', 'local')
    })

# ============================================
# Echo API (يعيد ما ترسله)
# ============================================
@app.route('/api/echo', methods=['GET', 'POST'])
def echo():
    if request.method == 'POST':
        data = request.get_json()
        return jsonify({
            "message": "تم استلام بياناتك",
            "received": data,
            "method": "POST"
        })
    else:
        return jsonify({
            "message": "هذا مسار Echo",
            "method": "GET",
            "params": dict(request.args)
        })

# ============================================
# الوقت الحالي
# ============================================
@app.route('/api/time')
def get_time():
    return jsonify({
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "UTC",
        "timestamp": datetime.now().timestamp()
    })

# ============================================
# معالجة الأخطاء
# ============================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "المسار غير موجود"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "خطأ داخلي في الخادم"}), 500

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("🚀 بدء تشغيل الخدمة الجديدة...")
    print(f"📡 الرابط: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)