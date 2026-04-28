from flask import Flask, jsonify, request
from flask_cors import CORS
import pg8000
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # السماح بالطلبات من أي مصدر (مفيد للموبايل)

# إعدادات قاعدة البيانات (استخدم متغيرات البيئة في الإنتاج)
DB_CONFIG = {
    "host": "dpg-d7ob38kvikkc73bpjpu0-a.oregon-postgres.render.com",
    "port": 5432,
    "database": "k_df2d",
    "user": "k_df2d_user",
    "password": "lnnilRfCTZpJevT7tZL1GAmyinyXPyZY",
    "ssl_context": True
}

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    return pg8000.connect(**DB_CONFIG)

# ============================================
# المسارات (Routes)
# ============================================

@app.route('/')
def home():
    """الصفحة الرئيسية - اختبار بسيط"""
    return jsonify({
        "status": "ok",
        "message": "🚀 API يعمل على Render بنجاح!",
        "time": datetime.now().isoformat(),
        "endpoints": [
            "/",
            "/health",
            "/db/test",
            "/data (GET, POST)",
            "/data/<int:id> (GET, DELETE)"
        ]
    })

@app.route('/health')
def health():
    """فحص صحة الخادم"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/db/test')
def test_db():
    """اختبار الاتصال بقاعدة البيانات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT NOW() as current_time, version() as pg_version")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "connected",
            "time": result[0].isoformat(),
            "postgres_version": result[1],
            "message": "✅ قاعدة البيانات تعمل بشكل طبيعي"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/data', methods=['GET'])
def get_all_data():
    """استرجاع جميع البيانات من جدول test_python"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, message, created_at 
            FROM test_python 
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        data = [
            {
                "id": row[0],
                "message": row[1],
                "created_at": row[2].isoformat() if row[2] else None
            }
            for row in rows
        ]
        
        return jsonify({
            "status": "success",
            "count": len(data),
            "data": data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/data', methods=['POST'])
def add_data():
    """إضافة بيانات جديدة إلى جدول test_python"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "status": "error",
                "message": "الرجاء إرسال { 'message': 'نص الرسالة' }"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO test_python (message) VALUES (%s) RETURNING id",
            (data['message'],)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "تم إضافة البيانات بنجاح",
            "id": new_id
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/data/<int:id>', methods=['GET'])
def get_one_data(id):
    """استرجاع بيانات واحدة حسب ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, message, created_at FROM test_python WHERE id = %s",
            (id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return jsonify({
                "status": "error",
                "message": f"لا توجد بيانات ذات ID: {id}"
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {
                "id": row[0],
                "message": row[1],
                "created_at": row[2].isoformat() if row[2] else None
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/data/<int:id>', methods=['DELETE'])
def delete_data(id):
    """حذف بيانات حسب ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM test_python WHERE id = %s RETURNING id",
            (id,)
        )
        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not deleted:
            return jsonify({
                "status": "error",
                "message": f"لا توجد بيانات ذات ID: {id}"
            }), 404
        
        return jsonify({
            "status": "success",
            "message": f"تم حذف البيانات ذات ID: {id}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================
# تشغيل الخادم
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
