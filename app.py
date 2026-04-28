"""
خادم API احترافي مع واجهة HTML
يدعم: قاعدة البيانات، المصادقة، لوحة تحكم ويب
"""

from flask import Flask, jsonify, request, render_template_string, redirect, url_for, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pg8000
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

# ============================================
# تهيئة التطبيق
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
CORS(app)

# الحد من الطلبات
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ============================================
# إعدادات قاعدة البيانات
# ============================================
DB_CONFIG = {
    "host": os.environ.get('PGHOST', 'dpg-d7ob38kvikkc73bpjpu0-a.oregon-postgres.render.com'),
    "port": int(os.environ.get('PGPORT', 5432)),
    "database": os.environ.get('PGDATABASE', 'k_df2d'),
    "user": os.environ.get('PGUSER', 'k_df2d_user'),
    "password": os.environ.get('PGPASSWORD', 'lnnilRfCTZpJevT7tZL1GAmyinyXPyZY'),
    "ssl_context": True
}

def get_db():
    return pg8000.connect(**DB_CONFIG)

def init_db():
    """إنشاء الجداول الأساسية"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            body TEXT,
            tags TEXT[],
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # إضافة مستخدم admin افتراضي إذا لم يكن موجوداً
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, is_admin)
            VALUES (%s, %s, %s, %s, %s)
        """, ('admin', 'admin@example.com', admin_pass, 'مدير النظام', True))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ تم تهيئة قاعدة البيانات")

# ============================================
# دوال مساعدة
# ============================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ============================================
# واجهة HTML (لوحة التحكم)
# ============================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة تحكم API - {{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
        }
        
        /* شريط التنقل */
        .navbar {
            background: rgba(15, 25, 45, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            border-bottom: 1px solid #e94560;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: bold;
            color: #e94560;
        }
        
        .logo span {
            color: #fff;
        }
        
        .nav-links {
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
        }
        
        .nav-links a {
            color: #eee;
            text-decoration: none;
            transition: color 0.3s;
        }
        
        .nav-links a:hover {
            color: #e94560;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .logout-btn {
            background: #e94560;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            color: white;
            text-decoration: none;
        }
        
        .logout-btn:hover {
            background: #ff6b8b;
        }
        
        /* الحاوية الرئيسية */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* البطاقات */
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h2 {
            color: #e94560;
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .stat-card {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #e94560;
        }
        
        /* الجداول */
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 0.75rem;
            text-align: right;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        th {
            background: rgba(233, 69, 96, 0.3);
            color: #e94560;
        }
        
        tr:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        /* النماذج */
        .form-group {
            margin-bottom: 1rem;
        }
        
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #ccc;
        }
        
        input, textarea, select {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #333;
            border-radius: 8px;
            background: #0f0f23;
            color: #fff;
            font-size: 1rem;
        }
        
        button, .btn {
            background: #e94560;
            color: white;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }
        
        button:hover, .btn:hover {
            background: #ff6b8b;
            transform: translateY(-2px);
        }
        
        .btn-danger {
            background: #dc3545;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .btn-success {
            background: #28a745;
        }
        
        /* رسائل التنبيه */
        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .alert-success {
            background: #28a74533;
            border: 1px solid #28a745;
            color: #28a745;
        }
        
        .alert-error {
            background: #dc354533;
            border: 1px solid #dc3545;
            color: #dc3545;
        }
        
        /* API endpoint */
        .endpoint {
            background: #0f0f23;
            padding: 0.5rem;
            border-radius: 6px;
            font-family: monospace;
            margin: 0.5rem 0;
        }
        
        /* استجابة للجوال */
        @media (max-width: 768px) {
            .navbar {
                flex-direction: column;
                text-align: center;
            }
            
            .container {
                padding: 1rem;
            }
            
            table {
                font-size: 0.8rem;
            }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">
            API <span>مدير المحتوى</span>
        </div>
        <div class="nav-links">
            <a href="{{ url_for('dashboard') }}">🏠 الرئيسية</a>
            <a href="{{ url_for('dashboard_contents') }}">📄 المحتوى</a>
            <a href="{{ url_for('dashboard_api') }}">🔌 API</a>
            {% if is_admin %}
            <a href="{{ url_for('dashboard_users') }}">👥 المستخدمين</a>
            {% endif %}
        </div>
        <div class="user-info">
            <span>👤 {{ username }}</span>
            <a href="{{ url_for('logout') }}" class="logout-btn">🚪 خروج</a>
        </div>
    </nav>
    
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

# ============================================
# صفحات الويب (Web Routes)
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """صفحة تسجيل الدخول"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash, is_admin FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and user[2] == hash_password(password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[3]
            return redirect(url_for('dashboard'))
        
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تسجيل الدخول - API</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .login-card {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                padding: 2rem;
                border-radius: 16px;
                width: 100%;
                max-width: 400px;
                text-align: center;
            }
            h1 { color: #e94560; margin-bottom: 1.5rem; }
            input {
                width: 100%;
                padding: 0.75rem;
                margin: 0.5rem 0;
                border: none;
                border-radius: 8px;
                background: #0f0f23;
                color: white;
            }
            button {
                background: #e94560;
                color: white;
                padding: 0.75rem;
                border: none;
                border-radius: 8px;
                width: 100%;
                cursor: pointer;
                margin-top: 1rem;
            }
            .alert {
                background: #dc354533;
                padding: 0.5rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                color: #dc3545;
            }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h1>🔐 تسجيل الدخول</h1>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for category, message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endwith %}
            <form method="POST">
                <input type="text" name="username" placeholder="اسم المستخدم" required>
                <input type="password" name="password" placeholder="كلمة المرور" required>
                <button type="submit">دخول</button>
            </form>
            <p style="margin-top: 1rem; font-size: 0.8rem;">المستخدم الافتراضي: admin / admin123</p>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/')
def dashboard():
    """لوحة التحكم الرئيسية"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM contents")
    contents_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(views) FROM contents")
    total_views = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM contents WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'")
    new_this_week = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, 
        title="الرئيسية",
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        content='''
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">''' + str(contents_count) + '''</div><div>المحتوى</div></div>
            <div class="stat-card"><div class="stat-number">''' + str(users_count) + '''</div><div>المستخدمين</div></div>
            <div class="stat-card"><div class="stat-number">''' + str(total_views) + '''</div><div>مشاهدة</div></div>
            <div class="stat-card"><div class="stat-number">''' + str(new_this_week) + '''</div><div>جديد هذا الأسبوع</div></div>
        </div>
        <div class="card">
            <h2>📡 حالة الخادم</h2>
            <div class="endpoint">✅ API يعمل</div>
            <div class="endpoint">✅ قاعدة البيانات متصلة</div>
            <div class="endpoint">🌐 ' + request.host + '</div>
        </div>
        ''')
    
@app.route('/dashboard/contents')
@login_required
def dashboard_contents():
    """إدارة المحتوى"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.title, c.body, c.views, c.created_at, u.username
        FROM contents c
        JOIN users u ON c.user_id = u.id
        ORDER BY c.id DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    contents_html = '<table>\n'
    contents_html += '<thead><tr><th>ID</th><th>العنوان</th><th>المحتوى</th><th>مشاهدات</th><th>الناشر</th><th>التاريخ</th><th>إجراءات</th></tr></thead><tbody>'
    for row in rows:
        contents_html += f'''
        <tr>
            <td>{row[0]}</td>
            <td>{row[1][:30]}</td>
            <td>{row[2][:50] if row[2] else ''}...</td>
            <td>{row[3]}</td>
            <td>{row[5]}</td>
            <td>{row[4].strftime('%Y-%m-%d') if row[4] else '-'}</td>
            <td>
                <form method="POST" action="/dashboard/contents/delete/{row[0]}" style="display:inline">
                    <button type="submit" class="btn-danger" style="padding:0.25rem 0.5rem;font-size:0.8rem;">🗑️ حذف</button>
                </form>
            </td>
        </tr>
        '''
    contents_html += '</tbody></table>'
    
    return render_template_string(HTML_TEMPLATE,
        title="المحتوى",
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        content=f'''
        <div class="card">
            <h2>➕ إضافة محتوى جديد</h2>
            <form method="POST" action="/dashboard/contents/add">
                <div class="form-group"><label>العنوان</label><input type="text" name="title" required></div>
                <div class="form-group"><label>المحتوى</label><textarea name="body" rows="4" required></textarea></div>
                <button type="submit" class="btn-success">➕ نشر</button>
            </form>
        </div>
        <div class="card">
            <h2>📄 المحتوى المنشور</h2>
            {contents_html}
        </div>
        ''')
    
@app.route('/dashboard/contents/add', methods=['POST'])
@login_required
def add_content_web():
    title = request.form.get('title')
    body = request.form.get('body')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contents (user_id, title, body) VALUES (%s, %s, %s)",
        (session['user_id'], title, body)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('تم إضافة المحتوى بنجاح', 'success')
    return redirect(url_for('dashboard_contents'))

@app.route('/dashboard/contents/delete/<int:content_id>', methods=['POST'])
@login_required
def delete_content_web(content_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contents WHERE id = %s", (content_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('تم حذف المحتوى', 'success')
    return redirect(url_for('dashboard_contents'))

@app.route('/dashboard/api')
@login_required
def dashboard_api():
    """صفحة توثيق API"""
    api_html = '''
    <div class="card">
        <h2>🔌 توثيق API</h2>
        <p>جميع نقاط النهاية تعيد بيانات بصيغة JSON</p>
        
        <h3>📡 النقاط العامة</h3>
        <div class="endpoint">GET /api/contents - عرض جميع المحتويات</div>
        <div class="endpoint">GET /api/contents/&lt;id&gt; - عرض محتوى محدد</div>
        <div class="endpoint">GET /api/stats - إحصائيات عامة</div>
        
        <h3>🔐 نقاط تحتاج توثيق (Bearer Token)</h3>
        <div class="endpoint">POST /api/contents - إضافة محتوى جديد</div>
        <div class="endpoint">PUT /api/contents/&lt;id&gt; - تعديل محتوى</div>
        <div class="endpoint">DELETE /api/contents/&lt;id&gt; - حذف محتوى</div>
        
        <h3>📝 مثال باستخدام Python</h3>
        <pre style="background:#0f0f23;padding:1rem;border-radius:8px;">
import requests

# عرض المحتويات
response = requests.get("https://''' + request.host + '''/api/contents")
print(response.json())

# إضافة محتوى جديد
response = requests.post(
    "https://''' + request.host + '''/api/contents",
    json={"title": "عنوان", "body": "محتوى"},
    headers={"Authorization": "Bearer your-api-key"}
)
        </pre>
    </div>
    '''
    
    return render_template_string(HTML_TEMPLATE,
        title="توثيق API",
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        content=api_html)

@app.route('/dashboard/users')
@admin_required
def dashboard_users():
    """إدارة المستخدمين (للمسؤول فقط)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, is_admin, created_at FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    users_html = '<table>\n'
    users_html += '<thead><tr><th>ID</th><th>المستخدم</th><th>البريد</th><th>الاسم الكامل</th><th>مسؤول</th><th>تاريخ التسجيل</th></tr></thead><tbody>'
    for row in rows:
        users_html += f'''
        <tr>
            <td>{row[0]}</td>
            <td>{row[1]}</td>
            <td>{row[2]}</td>
            <td>{row[3] or '-'}</td>
            <td>{'✅' if row[4] else '❌'}</td>
            <td>{row[5].strftime('%Y-%m-%d') if row[5] else '-'}</td>
        </tr>
        '''
    users_html += '</tbody></table>'
    
    return render_template_string(HTML_TEMPLATE,
        title="المستخدمين",
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        content=f'<div class="card"><h2>👥 المستخدمين</h2>{users_html}</div>')

# ============================================
# واجهة API (للتطبيقات الخارجية)
# ============================================

@app.route('/api/contents', methods=['GET'])
def api_get_contents():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, body, views, created_at FROM contents ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([{
        "id": r[0],
        "title": r[1],
        "body": r[2],
        "views": r[3],
        "created_at": r[4].isoformat() if r[4] else None
    } for r in rows])

@app.route('/api/contents', methods=['POST'])
def api_post_content():
    data = request.get_json()
    if not data or 'title' not in data or 'body' not in data:
        return jsonify({"error": "مطلوب title و body"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contents (user_id, title, body) VALUES (%s, %s, %s) RETURNING id",
        (1, data['title'], data['body'])
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"id": new_id, "message": "تم الإضافة"}), 201

@app.route('/api/contents/<int:content_id>', methods=['GET'])
def api_get_one_content(content_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET views = views + 1 WHERE id = %s", (content_id,))
    cursor.execute("SELECT id, title, body, views, created_at FROM contents WHERE id = %s", (content_id,))
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    
    if not row:
        return jsonify({"error": "غير موجود"}), 404
    
    return jsonify({
        "id": row[0],
        "title": row[1],
        "body": row[2],
        "views": row[3],
        "created_at": row[4].isoformat() if row[4] else None
    })

@app.route('/api/contents/<int:content_id>', methods=['DELETE'])
def api_delete_content(content_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contents WHERE id = %s RETURNING id", (content_id,))
    deleted = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    
    if not deleted:
        return jsonify({"error": "غير موجود"}), 404
    
    return jsonify({"message": "تم الحذف"})

@app.route('/api/stats', methods=['GET'])
def api_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contents")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(views), 0) FROM contents")
    views = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    return jsonify({
        "total_contents": total,
        "total_views": views,
        "api_version": "2.0.0",
        "server_time": datetime.now().isoformat()
    })

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    print("🚀 بدء تشغيل الخادم الاحترافي مع واجهة HTML...")
    init_db()
    print("✅ قاعدة البيانات جاهزة")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
