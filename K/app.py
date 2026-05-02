"""
نبض الحدث - مدونة عصرية متكاملة
للرفع على Render.com
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from datetime import datetime
import sqlite3
import os
import markdown
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nubd-alhadath-secret-key-2024')

# ========== قاعدة البيانات ==========
def init_db():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  content TEXT NOT NULL,
                  summary TEXT,
                  image_url TEXT,
                  category TEXT DEFAULT 'عام',
                  tags TEXT,
                  published BOOLEAN DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  is_admin BOOLEAN DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER,
                  author TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (post_id) REFERENCES posts(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS likes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER,
                  ip_address TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (post_id) REFERENCES posts(id))''')
    # إنشاء أدمن افتراضي إذا لم يكن موجودًا
    if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                 ('admin', generate_password_hash('admin123')))
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

# ========== مساعد الديكوريتور ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('صلاحيات غير كافية', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ========== قالب HTML عصري ==========
# ملاحظة: تم اختصار القالب هنا لتوفير المساحة، ولكن الكود الموجود في الأعلى هو نفسه
TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}نبض الحدث{% endblock %}</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --secondary: #7c3aed;
            --accent: #06b6d4;
            --dark: #0f172a;
            --light: #f8fafc;
            --gray: #64748b;
            --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-3: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.12);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 25px rgba(0,0,0,0.2);
            --shadow-xl: 0 20px 50px rgba(0,0,0,0.3);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Tajawal', sans-serif;
            background: var(--light);
            color: var(--dark);
            line-height: 1.8;
            min-height: 100vh;
        }

        .main-header {
            background: var(--gradient-1);
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: var(--shadow-lg);
        }

        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 2rem;
            font-weight: 900;
            color: white;
            text-decoration: none;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo i { font-size: 2.2rem; color: #fbbf24; }

        .nav-links {
            display: flex;
            gap: 1.5rem;
            align-items: center;
            list-style: none;
        }

        .nav-links a {
            color: white;
            text-decoration: none;
            font-weight: 500;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .nav-links a:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }

        .btn-primary {
            background: white;
            color: var(--primary) !important;
            font-weight: bold;
            box-shadow: var(--shadow-md);
        }

        .btn-primary:hover {
            background: #fbbf24 !important;
            color: var(--dark) !important;
        }

        .hero {
            background: var(--gradient-2);
            padding: 4rem 2rem;
            text-align: center;
            color: white;
            position: relative;
            overflow: hidden;
        }

        .hero h1 {
            font-size: 3rem;
            font-weight: 900;
            margin-bottom: 1rem;
            position: relative;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
        }

        .hero p {
            font-size: 1.3rem;
            opacity: 0.9;
            position: relative;
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .posts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }

        .post-card {
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: var(--shadow-md);
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
        }

        .post-card:hover {
            transform: translateY(-10px);
            box-shadow: var(--shadow-xl);
        }

        .post-body {
            padding: 1.5rem;
        }

        .post-title {
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: var(--dark);
        }

        .post-summary {
            color: var(--gray);
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }

        .btn {
            padding: 0.7rem 2rem;
            border: none;
            border-radius: 25px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'Tajawal', sans-serif;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .footer {
            background: var(--dark);
            color: white;
            text-align: center;
            padding: 2rem;
            margin-top: 4rem;
        }

        .footer i { color: #fbbf24; }

        @media (max-width: 768px) {
            .posts-grid { grid-template-columns: 1fr; }
            .logo { font-size: 1.5rem; }
            .hero h1 { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <header class="main-header">
        <nav class="nav-container">
            <a href="{{ url_for('index') }}" class="logo">
                <i class="fas fa-globe-americas"></i> نبض الحدث
            </a>
            <ul class="nav-links">
                <li><a href="{{ url_for('index') }}"><i class="fas fa-home"></i> الرئيسية</a></li>
                {% if session.user_id %}
                    {% if session.is_admin %}
                        <li><a href="{{ url_for('admin') }}"><i class="fas fa-cog"></i> لوحة التحكم</a></li>
                        <li><a href="{{ url_for('new_post') }}"><i class="fas fa-plus-circle"></i> مقال جديد</a></li>
                    {% endif %}
                    <li><a href="{{ url_for('logout') }}"><i class="fas fa-sign-out-alt"></i> خروج</a></li>
                {% else %}
                    <li><a href="{{ url_for('login') }}"><i class="fas fa-sign-in-alt"></i> دخول</a></li>
                {% endif %}
            </ul>
        </nav>
    </header>

    <div class="hero">
        <h1>مرحباً بكم في نبض الحدث</h1>
        <p>مدونة عصرية لأحدث الأخبار والمقالات</p>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="container" style="margin-top: 1rem;">
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}

    <footer class="footer">
        <p>© 2024 <i class="fas fa-heart"></i> نبض الحدث - جميع الحقوق محفوظة</p>
    </footer>
</body>
</html>
'''

# ========== المسارات ==========
@app.route('/')
def index():
    try:
        db = get_db()
        # استخدام استعلام بسيط ومضمون
        posts = db.execute('SELECT * FROM posts WHERE published = 1 ORDER BY created_at DESC').fetchall()
        db.close()
        return render_template_string(TEMPLATE, posts=posts)
    except Exception as e:
        # في حالة حدوث خطأ، نعرض رسالة بسيطة
        return f"حدث خطأ: {str(e)}. تأكد من وجود جدول 'posts' في قاعدة البيانات."

@app.route('/post/<int:post_id>')
def view_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ? AND published = 1', (post_id,)).fetchone()
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    comments = db.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY created_at DESC', (post_id,)).fetchall()
    db.close()
    content_html = markdown.markdown(post['content'], extensions=['fenced_code', 'tables'])
    return render_template_string(TEMPLATE, post=post, comments=comments, content_html=content_html)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('مرحباً بك!', 'success')
            return redirect(url_for('admin' if user['is_admin'] else 'index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template_string(TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    posts = db.execute('SELECT * FROM posts ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template_string(TEMPLATE, posts=posts)

@app.route('/new-post', methods=['GET', 'POST'])
@admin_required
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        summary = request.form.get('summary', '')
        image_url = request.form.get('image_url', '')
        category = request.form.get('category', 'عام')
        tags = request.form.get('tags', '')
        db = get_db()
        db.execute('INSERT INTO posts (title, content, summary, image_url, category, tags) VALUES (?, ?, ?, ?, ?, ?)',
                  (title, content, summary, image_url, category, tags))
        db.commit()
        db.close()
        flash('تم نشر المقال بنجاح!', 'success')
        return redirect(url_for('admin'))
    return render_template_string(TEMPLATE)

# ========== بدء التطبيق ==========
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)