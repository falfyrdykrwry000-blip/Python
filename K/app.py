from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import sqlite3
import os
import markdown
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nubd-alhadath-secret-key-2024')
app.permanent_session_lifetime = timedelta(days=30)

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

def init_db():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, content TEXT NOT NULL,
                  summary TEXT, image_url TEXT, category TEXT DEFAULT 'عام', tags TEXT,
                  published BOOLEAN DEFAULT 1, views INTEGER DEFAULT 0, user_id INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT,
                  password_hash TEXT, is_admin BOOLEAN DEFAULT 0, oauth_provider TEXT,
                  oauth_provider_id TEXT, bio TEXT DEFAULT '', website TEXT DEFAULT '',
                  avatar_url TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, author TEXT NOT NULL,
                  content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS likes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, user_id INTEGER,
                  ip_address TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users (username, email, password_hash, is_admin, bio) VALUES (?, ?, ?, ?, ?)",
                 ('admin', 'admin@krar.qzz.io', generate_password_hash('admin123'), 1, 'مدير المدونة'))
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

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
    user = db.execute('SELECT * FROM users WHERE oauth_provider = ? AND oauth_provider_id = ?',
                     (provider, provider_id)).fetchone()
    if not user:
        username = name or (email.split('@')[0] if email else provider + '_user')
        counter = 1
        original_username = username
        while db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            username = f"{original_username}{counter}"
            counter += 1
        db.execute('INSERT INTO users (username, email, password_hash, oauth_provider, oauth_provider_id) VALUES (?, ?, ?, ?, ?)',
                  (username, email, generate_password_hash(provider + str(provider_id)), provider, provider_id))
        db.commit()
        user = db.execute('SELECT * FROM users WHERE oauth_provider = ? AND oauth_provider_id = ?',
                         (provider, provider_id)).fetchone()
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
        return login_or_register_user('github', str(user_info['id']),
                                     user_info.get('name') or user_info.get('login'), email)
    except:
        flash('فشل تسجيل الدخول بـ GitHub', 'danger')
        return redirect(url_for('login'))

@app.route('/')
def index():
    db = get_db()
    posts = db.execute('''
        SELECT p.*, u.username as author_name, u.is_admin as author_is_admin,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.published = 1 ORDER BY p.created_at DESC
    ''').fetchall()
    categories = db.execute('SELECT DISTINCT category FROM posts WHERE published = 1').fetchall()
    db.close()
    return render_template('index.html', posts=posts, categories=categories)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    db = get_db()
    post = db.execute('''
        SELECT p.*, u.username as author_name, u.is_admin as author_is_admin, u.avatar_url as author_avatar,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.id = ? AND p.published = 1
    ''', (post_id,)).fetchone()
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    db.execute('UPDATE posts SET views = views + 1 WHERE id = ?', (post_id,))
    comments = db.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY created_at DESC', (post_id,)).fetchall()
    user_id = session.get('user_id')
    liked = db.execute('SELECT id FROM likes WHERE post_id = ? AND user_id = ?', (post_id, user_id)).fetchone() if user_id else None
    related = db.execute('SELECT * FROM posts WHERE category = ? AND id != ? AND published = 1 LIMIT 3',
                        (post['category'], post_id)).fetchall()
    db.commit()
    db.close()
    content_html = markdown.markdown(post['content'], extensions=['fenced_code', 'tables', 'codehilite'])
    return render_template('post.html', post=post, comments=comments,
                          content_html=content_html, liked=liked is not None, related=related)

@app.route('/category/<category>')
def category_posts(category):
    db = get_db()
    posts = db.execute('''
        SELECT p.*, u.username as author_name, u.is_admin as author_is_admin
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.category = ? AND p.published = 1 ORDER BY p.created_at DESC
    ''', (category,)).fetchall()
    db.close()
    return render_template('index.html', posts=posts, current_category=category)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        db = get_db()
        posts = db.execute('''
            SELECT p.*, u.username as author_name, u.is_admin as author_is_admin
            FROM posts p LEFT JOIN users u ON p.user_id = u.id
            WHERE p.published = 1 AND (p.title LIKE ? OR p.content LIKE ? OR p.tags LIKE ?)
            ORDER BY p.created_at DESC
        ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
        db.close()
    else:
        posts = []
    return render_template('index.html', posts=posts, search_query=query)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content', '')
    if not content.strip():
        flash('الرجاء كتابة تعليق', 'warning')
        return redirect(url_for('view_post', post_id=post_id))
    db = get_db()
    db.execute('INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)',
              (post_id, session.get('username', 'زائر'), content))
    db.commit()
    db.close()
    flash('تم إضافة التعليق بنجاح', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    user_id = session['user_id']
    db = get_db()
    existing = db.execute('SELECT id FROM likes WHERE post_id = ? AND user_id = ?', (post_id, user_id)).fetchone()
    if existing:
        db.execute('DELETE FROM likes WHERE id = ?', (existing['id'],))
        liked = False
    else:
        db.execute('INSERT INTO likes (post_id, user_id, ip_address) VALUES (?, ?, ?)',
                  (post_id, user_id, request.remote_addr))
        liked = True
    db.commit()
    count = db.execute('SELECT COUNT(*) as c FROM likes WHERE post_id = ?', (post_id,)).fetchone()['c']
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
        if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash(f'مرحباً بك، {username}!', 'success')
            return redirect(url_for('admin' if user['is_admin'] else 'index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        db = get_db()
        if db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            db.close()
            flash('اسم المستخدم موجود بالفعل', 'danger')
            return render_template('register.html')
        db.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                  (username, email, generate_password_hash(password)))
        db.commit()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        flash('تم إنشاء الحساب بنجاح!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    posts = db.execute('''
        SELECT p.*, u.username as author_name
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
    ''').fetchall()
    total_users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    total_comments = db.execute('SELECT COUNT(*) as c FROM comments').fetchone()['c']
    total_likes = db.execute('SELECT COUNT(*) as c FROM likes').fetchone()['c']
    db.close()
    return render_template('admin.html', posts=posts, total_posts=len(posts),
                          total_users=total_users, total_comments=total_comments, total_likes=total_likes)

@app.route('/new-post', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        db = get_db()
        db.execute('''INSERT INTO posts (title, content, summary, image_url, category, tags, user_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (request.form['title'], request.form['content'], request.form.get('summary', ''),
                   request.form.get('image_url', ''), request.form.get('category', 'عام'),
                   request.form.get('tags', ''), session['user_id']))
        db.commit()
        db.close()
        flash('تم نشر المقال بنجاح!', 'success')
        return redirect(url_for('my_posts'))
    return render_template('new_post.html')

@app.route('/my-posts')
@login_required
def my_posts():
    db = get_db()
    posts = db.execute('''
        SELECT p.*, u.username as author_name,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p LEFT JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ? ORDER BY p.created_at DESC
    ''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('my_posts.html', posts=posts)

@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    if post['user_id'] != session['user_id'] and not session.get('is_admin'):
        db.close()
        flash('لا تملك صلاحية تعديل هذا المقال', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        db.execute('''UPDATE posts SET title=?, content=?, summary=?, image_url=?, category=?, tags=?, published=?
                     WHERE id=?''',
                  (request.form['title'], request.form['content'], request.form.get('summary', ''),
                   request.form.get('image_url', ''), request.form.get('category', 'عام'),
                   request.form.get('tags', ''), 'published' in request.form, post_id))
        db.commit()
        db.close()
        flash('تم تحديث المقال بنجاح!', 'success')
        return redirect(url_for('my_posts'))
    db.close()
    return render_template('edit_post.html', post=post)

@app.route('/delete-post/<int:post_id>')
@login_required
def delete_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))
    if post['user_id'] != session['user_id'] and not session.get('is_admin'):
        db.close()
        flash('لا تملك صلاحية حذف هذا المقال', 'danger')
        return redirect(url_for('index'))
    db.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM likes WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.commit()
    db.close()
    flash('تم حذف المقال بنجاح', 'success')
    return redirect(url_for('my_posts'))

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    posts_count = db.execute('SELECT COUNT(*) as c FROM posts WHERE user_id = ?', (session['user_id'],)).fetchone()['c']
    comments_count = db.execute('SELECT COUNT(*) as c FROM comments WHERE author = ?', (session['username'],)).fetchone()['c']
    db.close()
    return render_template('profile.html', user=user, posts_count=posts_count, comments_count=comments_count)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        db = get_db()
        db.execute('UPDATE users SET bio=?, website=?, avatar_url=? WHERE id=?',
                  (request.form.get('bio', ''), request.form.get('website', ''),
                   request.form.get('avatar_url', ''), session['user_id']))
        db.commit()
        db.close()
        flash('تم تحديث الملف الشخصي', 'success')
        return redirect(url_for('profile'))
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    return render_template('edit_profile.html', user=user)

@app.route('/user/<username>')
def user_profile(username):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        db.close()
        return render_template('404.html'), 404
    posts = db.execute('SELECT * FROM posts WHERE user_id = ? AND published = 1 ORDER BY created_at DESC',
                      (user['id'],)).fetchall()
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