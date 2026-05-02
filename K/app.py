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
    # إنشاء أدمن افتراضي
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
TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}نبض الحدث{% endblock %}</title>
    <!-- خطوط عربية -->
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet">
    <!-- Font Awesome -->
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

        /* ===== الهيدر ===== */
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

        /* ===== البطل ===== */
        .hero {
            background: var(--gradient-2);
            padding: 4rem 2rem;
            text-align: center;
            color: white;
            position: relative;
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            animation: rotate 20s linear infinite;
        }

        @keyframes rotate {
            100% { transform: rotate(360deg); }
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

        /* ===== المحتوى ===== */
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

        .post-image {
            height: 200px;
            background: var(--gradient-3);
            position: relative;
            overflow: hidden;
        }

        .post-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .post-category {
            position: absolute;
            top: 15px;
            right: 15px;
            background: var(--secondary);
            color: white;
            padding: 0.3rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: bold;
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

        .post-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--gray);
            font-size: 0.85rem;
        }

        .post-stats {
            display: flex;
            gap: 1rem;
        }

        .post-stats span {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .btn-like {
            background: none;
            border: none;
            cursor: pointer;
            color: var(--gray);
            transition: color 0.3s;
            font-size: 1rem;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .btn-like:hover { color: #ef4444; }
        .btn-like.liked { color: #ef4444; }

        /* ===== صفحة التدوينة ===== */
        .single-post {
            background: white;
            border-radius: 20px;
            padding: 3rem;
            box-shadow: var(--shadow-lg);
            margin-top: 2rem;
        }

        .single-post h1 {
            font-size: 2.5rem;
            font-weight: 900;
            margin-bottom: 1rem;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .post-content {
            font-size: 1.1rem;
            line-height: 2;
            margin: 2rem 0;
        }

        .post-content img {
            max-width: 100%;
            border-radius: 15px;
        }

        .post-tags {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin: 1rem 0;
        }

        .tag {
            background: #e0e7ff;
            color: var(--primary);
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-size: 0.85rem;
        }

        /* ===== التعليقات ===== */
        .comments-section {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 2px solid #e2e8f0;
        }

        .comment {
            background: #f8fafc;
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 1rem;
            border-right: 4px solid var(--primary);
        }

        .comment-form textarea {
            width: 100%;
            padding: 1rem;
            border: 2px solid #e2e8f0;
            border-radius: 15px;
            font-family: 'Tajawal', sans-serif;
            margin: 1rem 0;
            resize: vertical;
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

        .btn-gradient {
            background: var(--gradient-1);
            color: white;
        }

        .btn-gradient:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        /* ===== الفوتر ===== */
        .footer {
            background: var(--dark);
            color: white;
            text-align: center;
            padding: 2rem;
            margin-top: 4rem;
        }

        .footer i { color: #fbbf24; }

        /* ===== نماذج ===== */
        .form-container {
            max-width: 500px;
            margin: 3rem auto;
            background: white;
            padding: 2rem;
            border-radius: 20px;
            box-shadow: var(--shadow-xl);
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 0.5rem;
            color: var(--dark);
        }

        .form-control {
            width: 100%;
            padding: 0.8rem 1rem;
            border: 2px solid #e2e8f0;
            border-radius: 15px;
            font-family: 'Tajawal', sans-serif;
            font-size: 1rem;
            transition: border-color 0.3s;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary);
        }

        .alert {
            padding: 1rem;
            border-radius: 15px;
            margin-bottom: 1rem;
            font-weight: 500;
        }

        .alert-success { background: #dcfce7; color: #166534; border-right: 4px solid #22c55e; }
        .alert-danger { background: #fee2e2; color: #991b1b; border-right: 4px solid #ef4444; }
        .alert-warning { background: #fef3c7; color: #92400e; border-right: 4px solid #f59e0b; }

        .admin-panel {
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 2rem;
            margin-top: 2rem;
        }

        .sidebar {
            background: white;
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: var(--shadow-md);
            height: fit-content;
        }

        .sidebar a {
            display: block;
            padding: 0.8rem 1rem;
            color: var(--dark);
            text-decoration: none;
            border-radius: 10px;
            margin-bottom: 0.5rem;
            transition: all 0.3s;
        }

        .sidebar a:hover, .sidebar a.active {
            background: var(--gradient-1);
            color: white;
        }

        @media (max-width: 768px) {
            .posts-grid { grid-template-columns: 1fr; }
            .admin-panel { grid-template-columns: 1fr; }
            .nav-links { gap: 0.5rem; }
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

    <script>
        // تأثير الإعجاب
        function toggleLike(postId) {
            fetch('/like/' + postId, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const btn = document.querySelector(`.btn-like[data-post="${postId}"]`);
                        const countSpan = document.getElementById(`likes-${postId}`);
                        if (data.liked) {
                            btn.classList.add('liked');
                            btn.innerHTML = '<i class="fas fa-heart"></i> ' + data.count;
                        } else {
                            btn.classList.remove('liked');
                            btn.innerHTML = '<i class="far fa-heart"></i> ' + data.count;
                        }
                    }
                });
        }
    </script>
</body>
</html>
'''

# ========== المسارات ==========
@app.route('/')
def index():
    db = get_db()
    posts = db.execute('''
        SELECT p.*, 
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p 
        WHERE published = 1 
        ORDER BY created_at DESC
    ''').fetchall()
    db.close()
    return render_template_string(TEMPLATE, posts=posts)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    db = get_db()
    post = db.execute('''
        SELECT p.*, 
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p 
        WHERE p.id = ? AND published = 1
    ''', (post_id,)).fetchone()
    
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    
    comments = db.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY created_at DESC', (post_id,)).fetchall()
    ip = request.remote_addr
    liked = db.execute('SELECT id FROM likes WHERE post_id = ? AND ip_address = ?', (post_id, ip)).fetchone()
    db.close()
    
    content_html = markdown.markdown(post['content'], extensions=['fenced_code', 'tables'])
    
    return render_template_string(TEMPLATE, post=post, comments=comments, content_html=content_html, liked=liked is not None)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    author = request.form.get('author', 'زائر')
    content = request.form.get('content', '')
    
    if not content.strip():
        flash('الرجاء كتابة تعليق', 'warning')
        return redirect(url_for('view_post', post_id=post_id))
    
    db = get_db()
    db.execute('INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)',
              (post_id, author, content))
    db.commit()
    db.close()
    
    flash('تم إضافة التعليق بنجاح', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    ip = request.remote_addr
    db = get_db()
    
    existing = db.execute('SELECT id FROM likes WHERE post_id = ? AND ip_address = ?', (post_id, ip)).fetchone()
    
    if existing:
        db.execute('DELETE FROM likes WHERE id = ?', (existing['id'],))
        liked = False
    else:
        db.execute('INSERT INTO likes (post_id, ip_address) VALUES (?, ?)', (post_id, ip))
        liked = True
    
    db.commit()
    count = db.execute('SELECT COUNT(*) as count FROM likes WHERE post_id = ?', (post_id,)).fetchone()['count']
    db.close()
    
    return {'success': True, 'liked': liked, 'count': count}

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
    
    form_html = '''
    {% extends "' + TEMPLATE.replace("'", "\\'") + '" %}
    {% block title %}تسجيل الدخول - نبض الحدث{% endblock %}
    {% block content %}
    <div class="form-container">
        <h2 style="text-align: center; margin-bottom: 2rem; color: var(--primary);">
            <i class="fas fa-sign-in-alt"></i> تسجيل الدخول
        </h2>
        <form method="POST">
            <div class="form-group">
                <label>اسم المستخدم</label>
                <input type="text" name="username" class="form-control" required>
            </div>
            <div class="form-group">
                <label>كلمة المرور</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-gradient" style="width: 100%;">
                <i class="fas fa-sign-in-alt"></i> دخول
            </button>
        </form>
    </div>
    {% endblock %}
    '''
    return render_template_string(form_html)

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
    
    admin_html = '''
    {% extends "' + TEMPLATE.replace("'", "\\'") + '" %}
    {% block title %}لوحة التحكم - نبض الحدث{% endblock %}
    {% block content %}
    <div class="container">
        <div class="admin-panel">
            <div class="sidebar">
                <h3><i class="fas fa-tachometer-alt"></i> لوحة التحكم</h3>
                <a href="{{ url_for(\'admin\') }}" class="active"><i class="fas fa-list"></i> جميع المقالات</a>
                <a href="{{ url_for(\'new_post\') }}"><i class="fas fa-plus-circle"></i> مقال جديد</a>
                <a href="{{ url_for(\'index\') }}"><i class="fas fa-eye"></i> معاينة المدونة</a>
                <a href="{{ url_for(\'logout\') }}"><i class="fas fa-sign-out-alt"></i> تسجيل الخروج</a>
            </div>
            <div>
                <h2>جميع المقالات</h2>
                {% if posts %}
                    {% for post in posts %}
                    <div class="post-card" style="margin-bottom: 1rem;">
                        <div class="post-body">
                            <h3>{{ post.title }}</h3>
                            <p>{{ post.summary or 'لا يوجد ملخص' }}</p>
                            <div class="post-meta">
                                <span><i class="far fa-calendar"></i> {{ post.created_at[:10] }}</span>
                                <span>{{ 'منشور' if post.published else 'مسودة' }}</span>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <p>لا توجد مقالات بعد.</p>
                {% endif %}
            </div>
        </div>
    </div>
    {% endblock %}
    '''
    return render_template_string(admin_html, posts=posts)

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
        db.execute('''INSERT INTO posts (title, content, summary, image_url, category, tags)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (title, content, summary, image_url, category, tags))
        db.commit()
        db.close()
        
        flash('تم نشر المقال بنجاح!', 'success')
        return redirect(url_for('admin'))
    
    post_form_html = '''
    {% extends "' + TEMPLATE.replace("'", "\\'") + '" %}
    {% block title %}مقال جديد - نبض الحدث{% endblock %}
    {% block content %}
    <div class="container" style="max-width: 800px;">
        <h2 style="margin: 2rem 0;"><i class="fas fa-pen-fancy"></i> كتابة مقال جديد</h2>
        <form method="POST" style="background: white; padding: 2rem; border-radius: 20px; box-shadow: var(--shadow-lg);">
            <div class="form-group">
                <label>العنوان</label>
                <input type="text" name="title" class="form-control" required>
            </div>
            <div class="form-group">
                <label>الملخص</label>
                <input type="text" name="summary" class="form-control">
            </div>
            <div class="form-group">
                <label>رابط الصورة</label>
                <input type="url" name="image_url" class="form-control" placeholder="https://...">
            </div>
            <div class="form-group">
                <label>التصنيف</label>
                <select name="category" class="form-control">
                    <option value="عام">عام</option>
                    <option value="تقنية">تقنية</option>
                    <option value="سياسة">سياسة</option>
                    <option value="رياضة">رياضة</option>
                    <option value="ثقافة">ثقافة</option>
                </select>
            </div>
            <div class="form-group">
                <label>الوسوم (مفصولة بفواصل)</label>
                <input type="text" name="tags" class="form-control" placeholder="تقنية, ذكاء اصطناعي">
            </div>
            <div class="form-group">
                <label>المحتوى (يدعم Markdown)</label>
                <textarea name="content" class="form-control" rows="15" required></textarea>
            </div>
            <button type="submit" class="btn btn-gradient">
                <i class="fas fa-paper-plane"></i> نشر المقال
            </button>
        </form>
    </div>
    {% endblock %}
    '''
    return render_template_string(post_form_html)

# ========== صفحة الخطأ ==========
@app.errorhandler(404)
def not_found(e):
    return render_template_string(TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <div style="text-align: center; padding: 4rem 2rem;">
            <i class="fas fa-exclamation-triangle" style="font-size: 5rem; color: #f59e0b;"></i>
            <h1 style="font-size: 3rem; margin: 1rem 0;">404</h1>
            <p>عذراً، الصفحة غير موجودة</p>
            <a href="/" class="btn btn-gradient">العودة للرئيسية</a>
        </div>
    ''')), 404

# ========== بدء التطبيق ==========
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)