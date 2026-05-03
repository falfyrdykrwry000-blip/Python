from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
import markdown
import pg8000.native
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nubd-alhadath-secret-key-2024')
app.permanent_session_lifetime = timedelta(days=30)

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def parse_db_url(url):
    url = url.replace('postgresql://', '')
    auth, rest = url.split('@')
    user, password = auth.split(':')
    host_port, dbname = rest.split('/')
    if ':' in host_port:
        host, port = host_port.split(':')
        port = int(port)
    else:
        host = host_port
        port = 5432
    return {'host': host, 'port': port, 'user': user, 'password': password, 'database': dbname}

def get_db():
    config = parse_db_url(DATABASE_URL)
    return pg8000.native.Connection(
        host=config['host'], port=config['port'],
        user=config['user'], password=config['password'],
        database=config['database']
    )

def init_db():
    conn = get_db()
    conn.run('''
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
            summary TEXT DEFAULT '', image_url TEXT DEFAULT '',
            category TEXT DEFAULT 'عام', tags TEXT DEFAULT '',
            published BOOLEAN DEFAULT TRUE, views INTEGER DEFAULT 0,
            user_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            email TEXT DEFAULT '', password_hash TEXT DEFAULT '',
            is_admin BOOLEAN DEFAULT FALSE, oauth_provider TEXT DEFAULT '',
            oauth_provider_id TEXT DEFAULT '', bio TEXT DEFAULT '',
            website TEXT DEFAULT '', avatar_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY, post_id INTEGER,
            author TEXT NOT NULL, content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.run('''
        CREATE TABLE IF NOT EXISTS likes (
            id SERIAL PRIMARY KEY, post_id INTEGER, user_id INTEGER,
            ip_address TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    rows = conn.run("SELECT * FROM users WHERE username='admin'")
    if not rows:
        conn.run("INSERT INTO users (username, email, password_hash, is_admin, bio) VALUES (:u, :e, :p, :a, :b)",
                 u='admin', e='admin@example.com', p=generate_password_hash('admin123'), a=True, b='مدير المدونة')
    conn.close()

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
    conn = get_db()
    rows = conn.run("SELECT * FROM users WHERE oauth_provider = :p AND oauth_provider_id = :i", p=provider, i=provider_id)
    if not rows:
        username = name or (email.split('@')[0] if email else provider + '_user')
        counter = 1
        original_username = username
        while conn.run("SELECT id FROM users WHERE username = :u", u=username):
            username = f"{original_username}{counter}"
            counter += 1
        conn.run("INSERT INTO users (username, email, password_hash, oauth_provider, oauth_provider_id) VALUES (:u, :e, :p, :pr, :i)",
                 u=username, e=email, p=generate_password_hash(provider + str(provider_id)), pr=provider, i=provider_id)
        rows = conn.run("SELECT * FROM users WHERE oauth_provider = :p AND oauth_provider_id = :i", p=provider, i=provider_id)
    if rows:
        user = rows[0]
        session.permanent = True
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['is_admin'] = user[4]
        flash(f'أهلاً بك، {user[1]}!', 'success')
        conn.close()
        return redirect(url_for('index'))
    conn.close()
    return redirect(url_for('login'))

@app.route('/login/google')
def google_login():
    if not GOOGLE_CLIENT_ID: flash('تسجيل Google غير مفعل', 'warning'); return redirect(url_for('login'))
    google = OAuth2Session(GOOGLE_CLIENT_ID, scope=GOOGLE_SCOPE, redirect_uri=url_for('google_callback', _external=True))
    auth_url, state = google.authorization_url(GOOGLE_AUTH_URL, access_type="offline", prompt="select_account")
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/login/google/callback')
def google_callback():
    google = OAuth2Session(GOOGLE_CLIENT_ID, state=session.get('oauth_state'), redirect_uri=url_for('google_callback', _external=True))
    try:
        token = google.fetch_token(GOOGLE_TOKEN_URL, client_secret=GOOGLE_CLIENT_SECRET, authorization_response=request.url)
        user_info = google.get(GOOGLE_USERINFO_URL).json()
        return login_or_register_user('google', user_info['id'], user_info.get('name'), user_info.get('email'))
    except:
        flash('فشل تسجيل الدخول بـ Google', 'danger')
        return redirect(url_for('login'))

@app.route('/login/github')
def github_login():
    if not GITHUB_CLIENT_ID: flash('تسجيل GitHub غير مفعل', 'warning'); return redirect(url_for('login'))
    github = OAuth2Session(GITHUB_CLIENT_ID, scope=GITHUB_SCOPE, redirect_uri=url_for('github_callback', _external=True))
    auth_url, state = github.authorization_url(GITHUB_AUTH_URL)
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/login/github/callback')
def github_callback():
    github = OAuth2Session(GITHUB_CLIENT_ID, state=session.get('oauth_state'), redirect_uri=url_for('github_callback', _external=True))
    try:
        token = github.fetch_token(GITHUB_TOKEN_URL, client_secret=GITHUB_CLIENT_SECRET, authorization_response=request.url)
        user_info = github.get(GITHUB_USERINFO_URL).json()
        return login_or_register_user('github', str(user_info['id']), user_info.get('name') or user_info.get('login'), user_info.get('email'))
    except:
        flash('فشل تسجيل الدخول بـ GitHub', 'danger')
        return redirect(url_for('login'))

@app.route('/')
def index():
    conn = get_db()
    posts = conn.run('''SELECT p.*, u.username as author_name, u.is_admin as author_is_admin,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
               FROM posts p LEFT JOIN users u ON p.user_id = u.id
               WHERE p.published = TRUE ORDER BY p.created_at DESC''')
    cats = conn.run('SELECT DISTINCT category FROM posts WHERE published = TRUE')
    categories = [c[0] for c in cats]
    conn.close()
    posts_list = [{'id': p[0], 'title': p[1], 'content': p[2], 'summary': p[3], 'image_url': p[4],
                   'category': p[5], 'tags': p[6], 'published': p[7], 'views': p[8], 'user_id': p[9],
                   'created_at': p[10], 'author_name': p[11], 'author_is_admin': p[12],
                   'comment_count': p[13] if len(p) > 13 else 0, 'like_count': p[14] if len(p) > 14 else 0} for p in posts]
    return render_template('index.html', posts=posts_list, categories=categories)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    conn = get_db()
    rows = conn.run('''SELECT p.*, u.username as author_name, u.is_admin as author_is_admin, u.avatar_url as author_avatar,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
               FROM posts p LEFT JOIN users u ON p.user_id = u.id
               WHERE p.id = :id AND p.published = TRUE''', id=post_id)
    if not rows: conn.close(); flash('المقال غير موجود', 'danger'); return redirect(url_for('index'))
    p = rows[0]
    conn.run('UPDATE posts SET views = views + 1 WHERE id = :id', id=post_id)
    comments = conn.run('SELECT * FROM comments WHERE post_id = :id ORDER BY created_at DESC', id=post_id)
    user_id = session.get('user_id')
    liked = conn.run('SELECT id FROM likes WHERE post_id = :p AND user_id = :u', p=post_id, u=user_id) if user_id else []
    related = conn.run('SELECT * FROM posts WHERE category = :c AND id != :i AND published = TRUE LIMIT 3', c=p[5], i=post_id)
    conn.close()
    post = {'id': p[0], 'title': p[1], 'content': p[2], 'summary': p[3], 'image_url': p[4],
            'category': p[5], 'tags': p[6], 'published': p[7], 'views': p[8], 'user_id': p[9],
            'created_at': p[10], 'author_name': p[11], 'author_is_admin': p[12], 'author_avatar': p[13],
            'like_count': p[14]}
    content_html = markdown.markdown(post['content'], extensions=['fenced_code', 'tables'])
    return render_template('post.html', post=post, comments=comments, content_html=content_html,
                          liked=len(liked) > 0 if liked else False, related=related)

@app.route('/category/<category>')
def category_posts(category):
    conn = get_db()
    posts = conn.run('''SELECT p.*, u.username as author_name, u.is_admin as author_is_admin
               FROM posts p LEFT JOIN users u ON p.user_id = u.id
               WHERE p.category = :c AND p.published = TRUE ORDER BY p.created_at DESC''', c=category)
    conn.close()
    posts_list = [{'id': p[0], 'title': p[1], 'content': p[2], 'summary': p[3], 'image_url': p[4],
                   'category': p[5], 'tags': p[6], 'published': p[7], 'views': p[8], 'user_id': p[9],
                   'created_at': p[10], 'author_name': p[11], 'author_is_admin': p[12]} for p in posts]
    return render_template('index.html', posts=posts_list, current_category=category)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        conn = get_db()
        posts = conn.run('''SELECT p.*, u.username as author_name, u.is_admin as author_is_admin
                   FROM posts p LEFT JOIN users u ON p.user_id = u.id
                   WHERE p.published = TRUE AND (p.title ILIKE :q OR p.content ILIKE :q OR p.tags ILIKE :q)
                   ORDER BY p.created_at DESC''', q=f'%{query}%')
        conn.close()
        posts_list = [{'id': p[0], 'title': p[1], 'content': p[2], 'summary': p[3], 'image_url': p[4],
                       'category': p[5], 'tags': p[6], 'published': p[7], 'views': p[8], 'user_id': p[9],
                       'created_at': p[10], 'author_name': p[11], 'author_is_admin': p[12]} for p in posts]
    else:
        posts_list = []
    return render_template('index.html', posts=posts_list, search_query=query)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content', '')
    if not content.strip(): flash('الرجاء كتابة تعليق', 'warning'); return redirect(url_for('view_post', post_id=post_id))
    conn = get_db()
    conn.run('INSERT INTO comments (post_id, author, content) VALUES (:p, :a, :c)',
             p=post_id, a=session.get('username', 'زائر'), c=content)
    conn.close()
    flash('تم إضافة التعليق بنجاح', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    user_id = session['user_id']
    conn = get_db()
    existing = conn.run('SELECT id FROM likes WHERE post_id = :p AND user_id = :u', p=post_id, u=user_id)
    if existing:
        conn.run('DELETE FROM likes WHERE id = :i', i=existing[0][0])
        liked = False
    else:
        conn.run('INSERT INTO likes (post_id, user_id, ip_address) VALUES (:p, :u, :ip)',
                 p=post_id, u=user_id, ip=request.remote_addr)
        liked = True
    count = conn.run('SELECT COUNT(*) FROM likes WHERE post_id = :p', p=post_id)[0][0]
    conn.close()
    return {'success': True, 'liked': liked, 'count': count}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        rows = conn.run('SELECT * FROM users WHERE username = :u', u=request.form['username'])
        conn.close()
        if rows and rows[0][3] and check_password_hash(rows[0][3], request.form['password']):
            user = rows[0]
            session.permanent = True
            session['user_id'] = user[0]; session['username'] = user[1]; session['is_admin'] = user[4]
            flash(f'مرحباً بك، {user[1]}!', 'success')
            return redirect(url_for('admin' if user[4] else 'index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db()
        if conn.run('SELECT id FROM users WHERE username = :u', u=request.form['username']):
            conn.close(); flash('اسم المستخدم موجود بالفعل', 'danger'); return render_template('register.html')
        conn.run('INSERT INTO users (username, email, password_hash) VALUES (:u, :e, :p)',
                 u=request.form['username'], e=request.form.get('email', ''), p=generate_password_hash(request.form['password']))
        rows = conn.run('SELECT * FROM users WHERE username = :u', u=request.form['username'])
        conn.close()
        user = rows[0]
        session.permanent = True; session['user_id'] = user[0]; session['username'] = user[1]; session['is_admin'] = user[4]
        flash('تم إنشاء الحساب بنجاح!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout(): session.clear(); flash('تم تسجيل الخروج', 'success'); return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    conn = get_db()
    posts = conn.run('''SELECT p.*, u.username as author_name FROM posts p LEFT JOIN users u ON p.user_id = u.id ORDER BY p.created_at DESC''')
    total_users = conn.run('SELECT COUNT(*) FROM users')[0][0]
    total_comments = conn.run('SELECT COUNT(*) FROM comments')[0][0]
    total_likes = conn.run('SELECT COUNT(*) FROM likes')[0][0]
    conn.close()
    posts_list = [{'id': p[0], 'title': p[1], 'content': p[2], 'summary': p[3], 'image_url': p[4],
                   'category': p[5], 'tags': p[6], 'published': p[7], 'views': p[8], 'user_id': p[9],
                   'created_at': p[10], 'author_name': p[11]} for p in posts]
    return render_template('admin.html', posts=posts_list, total_posts=len(posts_list),
                          total_users=total_users, total_comments=total_comments, total_likes=total_likes)

@app.route('/new-post', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        conn = get_db()
        conn.run('''INSERT INTO posts (title, content, summary, image_url, category, tags, user_id)
                    VALUES (:t, :c, :s, :i, :cat, :tag, :u)''',
                 t=request.form['title'], c=request.form['content'], s=request.form.get('summary', ''),
                 i=request.form.get('image_url', ''), cat=request.form.get('category', 'عام'),
                 tag=request.form.get('tags', ''), u=session['user_id'])
        conn.close()
        flash('تم نشر المقال بنجاح!', 'success')
        return redirect(url_for('my_posts'))
    return render_template('new_post.html')

@app.route('/my-posts')
@login_required
def my_posts():
    conn = get_db()
    posts = conn.run('''SELECT p.*, u.username as author_name,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
               FROM posts p LEFT JOIN users u ON p.user_id = u.id
               WHERE p.user_id = :u ORDER BY p.created_at DESC''', u=session['user_id'])
    conn.close()
    posts_list = [{'id': p[0], 'title': p[1], 'content': p[2], 'summary': p[3], 'image_url': p[4],
                   'category': p[5], 'tags': p[6], 'published': p[7], 'views': p[8], 'user_id': p[9],
                   'created_at': p[10], 'author_name': p[11], 'comment_count': p[12] if len(p) > 12 else 0,
                   'like_count': p[13] if len(p) > 13 else 0} for p in posts]
    return render_template('my_posts.html', posts=posts_list)

@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    conn = get_db()
    rows = conn.run('SELECT * FROM posts WHERE id = :i', i=post_id)
    if not rows: conn.close(); flash('المقال غير موجود', 'danger'); return redirect(url_for('index'))
    post = rows[0]
    if post[9] != session['user_id'] and not session.get('is_admin'):
        conn.close(); flash('لا تملك صلاحية', 'danger'); return redirect(url_for('index'))
    if request.method == 'POST':
        conn.run('''UPDATE posts SET title=:t, content=:c, summary=:s, image_url=:i, category=:cat, tags=:tag, published=:p
                    WHERE id=:id''',
                 t=request.form['title'], c=request.form['content'], s=request.form.get('summary', ''),
                 i=request.form.get('image_url', ''), cat=request.form.get('category', 'عام'),
                 tag=request.form.get('tags', ''), p='published' in request.form, id=post_id)
        conn.close(); flash('تم تحديث المقال!', 'success'); return redirect(url_for('my_posts'))
    conn.close()
    post_dict = {'id': post[0], 'title': post[1], 'content': post[2], 'summary': post[3], 'image_url': post[4],
                 'category': post[5], 'tags': post[6], 'published': post[7], 'views': post[8], 'user_id': post[9],
                 'created_at': post[10]}
    return render_template('edit_post.html', post=post_dict)

@app.route('/delete-post/<int:post_id>')
@login_required
def delete_post(post_id):
    conn = get_db()
    rows = conn.run('SELECT * FROM posts WHERE id = :i', i=post_id)
    if not rows: conn.close(); flash('المقال غير موجود', 'danger'); return redirect(url_for('index'))
    if rows[0][9] != session['user_id'] and not session.get('is_admin'):
        conn.close(); flash('لا تملك صلاحية', 'danger'); return redirect(url_for('index'))
    conn.run('DELETE FROM comments WHERE post_id = :p', p=post_id)
    conn.run('DELETE FROM likes WHERE post_id = :p', p=post_id)
    conn.run('DELETE FROM posts WHERE id = :p', p=post_id)
    conn.close(); flash('تم حذف المقال', 'success'); return redirect(url_for('my_posts'))

@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    rows = conn.run('SELECT * FROM users WHERE id = :u', u=session['user_id'])
    user = rows[0]
    posts_count = conn.run('SELECT COUNT(*) FROM posts WHERE user_id = :u', u=session['user_id'])[0][0]
    comments_count = conn.run('SELECT COUNT(*) FROM comments WHERE author = :a', a=session['username'])[0][0]
    conn.close()
    user_dict = {'id': user[0], 'username': user[1], 'email': user[2], 'is_admin': user[4],
                 'oauth_provider': user[5], 'bio': user[7] if len(user) > 7 else '',
                 'website': user[8] if len(user) > 8 else '', 'avatar_url': user[9] if len(user) > 9 else '',
                 'created_at': user[10] if len(user) > 10 else ''}
    return render_template('profile.html', user=user_dict, posts_count=posts_count, comments_count=comments_count)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        conn = get_db()
        conn.run('UPDATE users SET bio=:b, website=:w, avatar_url=:a WHERE id=:u',
                 b=request.form.get('bio', ''), w=request.form.get('website', ''),
                 a=request.form.get('avatar_url', ''), u=session['user_id'])
        conn.close(); flash('تم تحديث الملف الشخصي', 'success'); return redirect(url_for('profile'))
    conn = get_db()
    rows = conn.run('SELECT * FROM users WHERE id = :u', u=session['user_id'])
    conn.close()
    user = rows[0]
    user_dict = {'id': user[0], 'username': user[1], 'email': user[2], 'is_admin': user[4],
                 'oauth_provider': user[5], 'bio': user[7] if len(user) > 7 else '',
                 'website': user[8] if len(user) > 8 else '', 'avatar_url': user[9] if len(user) > 9 else '',
                 'created_at': user[10] if len(user) > 10 else ''}
    return render_template('edit_profile.html', user=user_dict)

@app.route('/user/<username>')
def user_profile(username):
    conn = get_db()
    rows = conn.run('SELECT * FROM users WHERE username = :u', u=username)
    if not rows: conn.close(); return render_template('404.html'), 404
    user = rows[0]
    posts = conn.run('SELECT * FROM posts WHERE user_id = :u AND published = TRUE ORDER BY created_at DESC', u=user[0])
    conn.close()
    user_dict = {'id': user[0], 'username': user[1], 'email': user[2], 'is_admin': user[4],
                 'oauth_provider': user[5], 'bio': user[7] if len(user) > 7 else '',
                 'website': user[8] if len(user) > 8 else '', 'avatar_url': user[9] if len(user) > 9 else '',
                 'created_at': user[10] if len(user) > 10 else ''}
    posts_list = [{'id': p[0], 'title': p[1], 'content': p[2], 'summary': p[3], 'image_url': p[4],
                   'category': p[5], 'tags': p[6], 'published': p[7], 'views': p[8], 'user_id': p[9],
                   'created_at': p[10]} for p in posts]
    return render_template('public_profile.html', user=user_dict, posts=posts_list, posts_count=len(posts_list))

@app.errorhandler(404)
def not_found(e): return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)