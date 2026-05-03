"""
نبض الحدث - مدونة عصرية مع PostgreSQL
للرفع على Render.com
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
import markdown
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nubd-alhadath-secret-key-2024')
app.permanent_session_lifetime = timedelta(days=30)

# ========== قاعدة البيانات ==========
DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            category TEXT DEFAULT 'عام',
            tags TEXT DEFAULT '',
            published BOOLEAN DEFAULT TRUE,
            views INTEGER DEFAULT 0,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT DEFAULT '',
            password_hash TEXT DEFAULT '',
            is_admin BOOLEAN DEFAULT FALSE,
            oauth_provider TEXT DEFAULT '',
            oauth_provider_id TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            website TEXT DEFAULT '',
            avatar_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id SERIAL PRIMARY KEY,
            post_id INTEGER,
            user_id INTEGER,
            ip_address TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, email, password_hash, is_admin, bio) VALUES (%s, %s, %s, %s, %s)",
                 ('admin', 'admin@example.com', generate_password_hash('admin123'), True, 'مدير المدونة'))
    conn.commit()
    conn.close()

# ========== OAuth ==========
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo'
GOOGLE_SCOPE = ['openid', 'email', 'profile']

GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
GITHUB_AUTH_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USERINFO_URL = 'https://api.github.com/user'
GITHUB_SCOPE = ['user:email']

# ========== الديكوريتور ==========
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
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('هذه الصفحة مخصصة للمشرفين فقط', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def login_or_register_user(provider, provider_id, name, email):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE oauth_provider = %s AND oauth_provider_id = %s", (provider, provider_id))
    user = c.fetchone()
    if not user:
        username = name or (email.split('@')[0] if email else provider + '_user')
        counter = 1
        original_username = username
        while True:
            c.execute("SELECT id FROM users WHERE username = %s", (username,))
            if not c.fetchone():
                break
            username = f"{original_username}{counter}"
            counter += 1
        c.execute("INSERT INTO users (username, email, password_hash, oauth_provider, oauth_provider_id) VALUES (%s, %s, %s, %s, %s) RETURNING *",
                 (username, email, generate_password_hash(provider + str(provider_id)), provider, provider_id))
        db.commit()
        user = c.fetchone()
    if user:
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        flash(f'أهلاً بك، {user["username"]}!', 'success')
        db.close()
        return redirect(url_for('index'))
    db.close()
    return redirect(url_for('login'))

# ========== OAuth Routes ==========
@app.route('/login/google')
def google_login():
    if not GOOGLE_CLIENT_ID:
        flash('تسجيل Google غير مفعل', 'warning')
        return redirect(url_for('login'))
    google = OAuth2Session(GOOGLE_CLIENT_ID, scope=GOOGLE_SCOPE,
                          redirect_uri=url_for('google_callback', _external=True))
    auth_url, state = google.authorization_url(GOOGLE_AUTH_URL, access_type="offline", prompt="select_account")
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/login/google/callback')
def google_callback():
    google = OAuth2Session(GOOGLE_CLIENT_ID, state=session.get('oauth_state'),
                          redirect_uri=url_for('google_callback', _external=True))
    try:
        token = google.fetch_token(GOOGLE_TOKEN_URL, client_secret=GOOGLE_CLIENT_SECRET,
                                  authorization_response=request.url)
        user_info = google.get(GOOGLE_USERINFO_URL).json()
        return login_or_register_user('google', user_info['id'], user_info.get('name'), user_info.get('email'))
    except:
        flash('فشل تسجيل الدخول بـ Google', 'danger')
        return redirect(url_for('login'))

@app.route('/login/github')
def github_login():
    if not GITHUB_CLIENT_ID:
        flash('تسجيل GitHub غير مفعل', 'warning')
        return redirect(url_for('login'))
    github = OAuth2Session(GITHUB_CLIENT_ID, scope=GITHUB_SCOPE,
                          redirect_uri=url_for('github_callback', _external=True))
    auth_url, state = github.authorization_url(GITHUB_AUTH_URL)
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/login/github/callback')
def github_callback():
    github = OAuth2Session(GITHUB_CLIENT_ID, state=session.get('oauth_state'),
                          redirect_uri=url_for('github_callback', _external=True))
    try:
        token = github.fetch_token(GITHUB_TOKEN_URL, client_secret=GITHUB_CLIENT_SECRET,
                                  authorization_response=request.url)
        user_info = github.get(GITHUB_USERINFO_URL).json()
        email = user_info.get('email')
        if not email:
            emails_resp = github.get('https://api.github.com/user/emails').json()
            email = next((e['email'] for e in emails_resp if e.get('primary')), None)
        return login_or_register_user('github', str(user_info['id']),
                                     user_info.get('name') or user_info.get('login'), email)
    except:
        flash('فشل تسجيل الدخول بـ GitHub', 'danger')
        return redirect(url_for('login'))

# ========== الصفحة الرئيسية ==========
@app.route('/')
def index():
    db = get_db()
    c = db.cursor()
    c.execute('''
        SELECT p.*, u.username as author_name, u.is_admin as author_is_admin,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.published = TRUE ORDER BY p.created_at DESC
    ''')
    posts = c.fetchall()
    c.execute('SELECT DISTINCT category FROM posts WHERE published = TRUE')
    categories = c.fetchall()
    db.close()
    return render_template('index.html', posts=posts, categories=categories)

# ========== عرض مقال ==========
@app.route('/post/<int:post_id>')
def view_post(post_id):
    db = get_db()
    c = db.cursor()
    c.execute('''
        SELECT p.*, u.username as author_name, u.is_admin as author_is_admin, u.avatar_url as author_avatar,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.id = %s AND p.published = TRUE
    ''', (post_id,))
    post = c.fetchone()
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    c.execute('UPDATE posts SET views = views + 1 WHERE id = %s', (post_id,))
    c.execute('SELECT * FROM comments WHERE post_id = %s ORDER BY created_at DESC', (post_id,))
    comments = c.fetchall()
    user_id = session.get('user_id')
    liked = None
    if user_id:
        c.execute('SELECT id FROM likes WHERE post_id = %s AND user_id = %s', (post_id, user_id))
        liked = c.fetchone()
    c.execute('SELECT * FROM posts WHERE category = %s AND id != %s AND published = TRUE LIMIT 3',
              (post['category'], post_id))
    related = c.fetchall()
    db.commit()
    db.close()
    content_html = markdown.markdown(post['content'], extensions=['fenced_code', 'tables', 'codehilite'])
    return render_template('post.html', post=post, comments=comments,
                          content_html=content_html, liked=liked is not None, related=related)

# ========== تصنيفات ==========
@app.route('/category/<category>')
def category_posts(category):
    db = get_db()
    c = db.cursor()
    c.execute('''
        SELECT p.*, u.username as author_name, u.is_admin as author_is_admin
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.category = %s AND p.published = TRUE ORDER BY p.created_at DESC
    ''', (category,))
    posts = c.fetchall()
    db.close()
    return render_template('index.html', posts=posts, current_category=category)

# ========== بحث ==========
@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        db = get_db()
        c = db.cursor()
        c.execute('''
            SELECT p.*, u.username as author_name, u.is_admin as author_is_admin
            FROM posts p LEFT JOIN users u ON p.user_id = u.id
            WHERE p.published = TRUE AND (p.title ILIKE %s OR p.content ILIKE %s OR p.tags ILIKE %s)
            ORDER BY p.created_at DESC
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        posts = c.fetchall()
        db.close()
    else:
        posts = []
    return render_template('index.html', posts=posts, search_query=query)

# ========== تعليقات ==========
@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content', '')
    if not content.strip():
        flash('الرجاء كتابة تعليق', 'warning')
        return redirect(url_for('view_post', post_id=post_id))
    db = get_db()
    c = db.cursor()
    c.execute('INSERT INTO comments (post_id, author, content) VALUES (%s, %s, %s)',
              (post_id, session.get('username', 'زائر'), content))
    db.commit()
    db.close()
    flash('تم إضافة التعليق بنجاح', 'success')
    return redirect(url_for('view_post', post_id=post_id))

# ========== إعجاب ==========
@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    user_id = session['user_id']
    db = get_db()
    c = db.cursor()
    c.execute('SELECT id FROM likes WHERE post_id = %s AND user_id = %s', (post_id, user_id))
    existing = c.fetchone()
    if existing:
        c.execute('DELETE FROM likes WHERE id = %s', (existing['id'],))
        liked = False
    else:
        c.execute('INSERT INTO likes (post_id, user_id, ip_address) VALUES (%s, %s, %s)',
                  (post_id, user_id, request.remote_addr))
        liked = True
    db.commit()
    c.execute('SELECT COUNT(*) as c FROM likes WHERE post_id = %s', (post_id,))
    count = c.fetchone()['c']
    db.close()
    return {'success': True, 'liked': liked, 'count': count}

# ========== تسجيل الدخول ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        c = db.cursor()
        c.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = c.fetchone()
        db.close()
        if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash(f'مرحباً بك، {username}!', 'success')
            return redirect(url_for('admin' if user['is_admin'] else 'index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')

# ========== تسجيل ==========
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        db = get_db()
        c = db.cursor()
        c.execute('SELECT id FROM users WHERE username = %s', (username,))
        if c.fetchone():
            db.close()
            flash('اسم المستخدم موجود بالفعل', 'danger')
            return render_template('register.html')
        c.execute('INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING *',
                  (username, email, generate_password_hash(password)))
        db.commit()
        user = c.fetchone()
        db.close()
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        flash('تم إنشاء الحساب بنجاح!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

# ========== تسجيل الخروج ==========
@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج', 'success')
    return redirect(url_for('index'))

# ========== لوحة تحكم ==========
@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    c = db.cursor()
    c.execute('''
        SELECT p.*, u.username as author_name
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
    ''')
    posts = c.fetchall()
    c.execute('SELECT COUNT(*) as c FROM users')
    total_users = c.fetchone()['c']
    c.execute('SELECT COUNT(*) as c FROM comments')
    total_comments = c.fetchone()['c']
    c.execute('SELECT COUNT(*) as c FROM likes')
    total_likes = c.fetchone()['c']
    db.close()
    return render_template('admin.html', posts=posts, total_posts=len(posts),
                          total_users=total_users, total_comments=total_comments, total_likes=total_likes)

# ========== مقال جديد ==========
@app.route('/new-post', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        db = get_db()
        c = db.cursor()
        c.execute('''INSERT INTO posts (title, content, summary, image_url, category, tags, user_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                  (request.form['title'], request.form['content'], request.form.get('summary', ''),
                   request.form.get('image_url', ''), request.form.get('category', 'عام'),
                   request.form.get('tags', ''), session['user_id']))
        db.commit()
        db.close()
        flash('تم نشر المقال بنجاح!', 'success')
        return redirect(url_for('my_posts'))
    return render_template('new_post.html')

# ========== منشوراتي ==========
@app.route('/my-posts')
@login_required
def my_posts():
    db = get_db()
    c = db.cursor()
    c.execute('''
        SELECT p.*, u.username as author_name,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.user_id = %s ORDER BY p.created_at DESC
    ''', (session['user_id'],))
    posts = c.fetchall()
    db.close()
    return render_template('my_posts.html', posts=posts)

# ========== تعديل مقال ==========
@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    db = get_db()
    c = db.cursor()
    c.execute('SELECT * FROM posts WHERE id = %s', (post_id,))
    post = c.fetchone()
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    if post['user_id'] != session['user_id'] and not session.get('is_admin'):
        db.close()
        flash('لا تملك صلاحية تعديل هذا المقال', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        c.execute('''UPDATE posts SET title=%s, content=%s, summary=%s, image_url=%s, category=%s, tags=%s, published=%s
                     WHERE id=%s''',
                  (request.form['title'], request.form['content'], request.form.get('summary', ''),
                   request.form.get('image_url', ''), request.form.get('category', 'عام'),
                   request.form.get('tags', ''), 'published' in request.form, post_id))
        db.commit()
        db.close()
        flash('تم تحديث المقال بنجاح!', 'success')
        return redirect(url_for('my_posts'))
    db.close()
    return render_template('edit_post.html', post=post)

# ========== حذف مقال ==========
@app.route('/delete-post/<int:post_id>')
@login_required
def delete_post(post_id):
    db = get_db()
    c = db.cursor()
    c.execute('SELECT * FROM posts WHERE id = %s', (post_id,))
    post = c.fetchone()
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    if post['user_id'] != session['user_id'] and not session.get('is_admin'):
        db.close()
        flash('لا تملك صلاحية حذف هذا المقال', 'danger')
        return redirect(url_for('index'))
    c.execute('DELETE FROM comments WHERE post_id = %s', (post_id,))
    c.execute('DELETE FROM likes WHERE post_id = %s', (post_id,))
    c.execute('DELETE FROM posts WHERE id = %s', (post_id,))
    db.commit()
    db.close()
    flash('تم حذف المقال بنجاح', 'success')
    return redirect(url_for('my_posts'))

# ========== ملف شخصي ==========
@app.route('/profile')
@login_required
def profile():
    db = get_db()
    c = db.cursor()
    c.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = c.fetchone()
    c.execute('SELECT COUNT(*) as c FROM posts WHERE user_id = %s', (session['user_id'],))
    posts_count = c.fetchone()['c']
    c.execute('SELECT COUNT(*) as c FROM comments WHERE author = %s', (session['username'],))
    comments_count = c.fetchone()['c']
    db.close()
    return render_template('profile.html', user=user, posts_count=posts_count, comments_count=comments_count)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        db = get_db()
        c = db.cursor()
        c.execute('UPDATE users SET bio=%s, website=%s, avatar_url=%s WHERE id=%s',
                  (request.form.get('bio', ''), request.form.get('website', ''),
                   request.form.get('avatar_url', ''), session['user_id']))
        db.commit()
        db.close()
        flash('تم تحديث الملف الشخصي', 'success')
        return redirect(url_for('profile'))
    db = get_db()
    c = db.cursor()
    c.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = c.fetchone()
    db.close()
    return render_template('edit_profile.html', user=user)

@app.route('/user/<username>')
def user_profile(username):
    db = get_db()
    c = db.cursor()
    c.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = c.fetchone()
    if not user:
        db.close()
        return render_template('404.html'), 404
    c.execute('SELECT * FROM posts WHERE user_id = %s AND published = TRUE ORDER BY created_at DESC', (user['id'],))
    posts = c.fetchall()
    db.close()
    return render_template('public_profile.html', user=user, posts=posts, posts_count=len(posts))

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)