from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
import json
import markdown
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from requests_oauthlib import OAuth2Session
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nubd-alhadath-secret-key-2024')
app.permanent_session_lifetime = timedelta(days=30)

# ========== إعدادات GitHub API ==========
GITHUB_TOKEN = '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'
GITHUB_USER = 'falfyrdykrwry000-blip'
GITHUB_REPO = 'storage'
GITHUB_API = f'https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents'
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# OAuth
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

# ========== دوال GitHub API ==========
def github_get_file(path):
    """قراءة ملف واحد من GitHub"""
    try:
        url = f'{GITHUB_API}/{path}'
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            return json.loads(content), data['sha']
        return None, None
    except Exception as e:
        print(f'github_get_file error: {e}')
        return None, None

def github_save(path, data, sha=None, message='تحديث'):
    """حفظ ملف في GitHub"""
    try:
        url = f'{GITHUB_API}/{path}'
        content = base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        ).decode('utf-8')
        body = {
            'message': message,
            'content': content,
            'branch': 'master'
        }
        if sha:
            body['sha'] = sha
        r = requests.put(url, headers=HEADERS, json=body)
        print(f'Save {path}: {r.status_code} - {r.text[:200]}')
        return r.status_code in [200, 201]
    except Exception as e:
        print(f'github_save error: {e}')
        return False

def github_delete(path, sha, message='حذف'):
    """حذف ملف من GitHub"""
    try:
        url = f'{GITHUB_API}/{path}'
        body = {'message': message, 'sha': sha, 'branch': 'master'}
        r = requests.delete(url, headers=HEADERS, json=body)
        return r.status_code == 200
    except:
        return False

# ========== دوال البيانات ==========
def get_users():
    data, _ = github_get_file('users.json')
    return data if data else {}

def save_users(users):
    _, sha = github_get_file('users.json')
    github_save('users.json', users, sha, 'تحديث المستخدمين')

def get_posts():
    """جلب جميع المقالات من مجلد posts"""
    try:
        url = f'https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/posts'
        r = requests.get(url, headers=HEADERS)
        posts = []
        if r.status_code == 200:
            for item in r.json():
                if item['name'].endswith('.json'):
                    file_url = item['url']
                    file_r = requests.get(file_url, headers=HEADERS)
                    if file_r.status_code == 200:
                        content = base64.b64decode(file_r.json()['content']).decode('utf-8')
                        try:
                            post = json.loads(content)
                            post['_file'] = item['name']
                            posts.append(post)
                        except:
                            pass
        posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return posts
    except Exception as e:
        print(f'get_posts error: {e}')
        return []

def get_post(post_id):
    """جلب مقال واحد من posts/post_id.json"""
    try:
        data, _ = github_get_file(f'posts/{post_id}.json')
        return data
    except Exception as e:
        print(f'get_post error: {e}')
        return None

def save_post(post_id, data, message='تحديث مقال'):
    """حفظ مقال في posts/post_id.json"""
    _, sha = github_get_file(f'posts/{post_id}.json')
    return github_save(f'posts/{post_id}.json', data, sha, message)

def delete_post_file(post_id):
    """حذف مقال"""
    _, sha = github_get_file(f'posts/{post_id}.json')
    if sha:
        return github_delete(f'posts/{post_id}.json', sha, 'حذف مقال')
    return False

def get_next_post_id():
    """الحصول على رقم المقال التالي"""
    posts = get_posts()
    if not posts:
        return 1
    return max(p.get('id', 0) for p in posts) + 1

def get_comments(post_id):
    """جلب تعليقات مقال"""
    data, _ = github_get_file(f'comments/{post_id}.json')
    return data if data else []

def save_comments(post_id, comments):
    """حفظ تعليقات مقال"""
    _, sha = github_get_file(f'comments/{post_id}.json')
    return github_save(f'comments/{post_id}.json', comments, sha, 'تحديث تعليقات')

def get_likes(post_id):
    """جلب إعجابات مقال"""
    data, _ = github_get_file(f'likes/{post_id}.json')
    return data if data else []

def save_likes(post_id, likes):
    """حفظ إعجابات مقال"""
    _, sha = github_get_file(f'likes/{post_id}.json')
    return github_save(f'likes/{post_id}.json', likes, sha, 'تحديث إعجابات')

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
    users = get_users()

    for uid, u in users.items():
        if u.get('oauth_provider') == provider and u.get('oauth_id') == provider_id:
            session.permanent = True
            session['user_id'] = uid
            session['username'] = u['username']
            session['is_admin'] = u.get('is_admin', False)
            flash(f'أهلاً بك، {u["username"]}!', 'success')
            return redirect(url_for('index'))

    uid = str(len(users) + 1)
    username = name or (email.split('@')[0] if email else f'{provider}_user')
    users[uid] = {
        'username': username,
        'email': email,
        'oauth_provider': provider,
        'oauth_id': provider_id,
        'is_admin': False,
        'bio': '',
        'website': '',
        'avatar_url': '',
        'created_at': datetime.now().isoformat()
    }
    save_users(users)

    session.permanent = True
    session['user_id'] = uid
    session['username'] = username
    session['is_admin'] = False
    flash(f'أهلاً بك، {username}!', 'success')
    return redirect(url_for('index'))

# ========== مسارات OAuth ==========
@app.route('/login/google')
def google_login():
    if not GOOGLE_CLIENT_ID:
        flash('تسجيل Google غير مفعل', 'warning')
        return redirect(url_for('login'))
    google = OAuth2Session(GOOGLE_CLIENT_ID, scope=GOOGLE_SCOPE,
                          redirect_uri=url_for('google_callback', _external=True))
    authorization_url, state = google.authorization_url(GOOGLE_AUTH_URL, access_type="offline", prompt="select_account")
    session['oauth_state'] = state
    return redirect(authorization_url)

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
    authorization_url, state = github.authorization_url(GITHUB_AUTH_URL)
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/login/github/callback')
def github_callback():
    github = OAuth2Session(GITHUB_CLIENT_ID, state=session.get('oauth_state'),
                          redirect_uri=url_for('github_callback', _external=True))
    try:
        token = github.fetch_token(GITHUB_TOKEN_URL, client_secret=GITHUB_CLIENT_SECRET,
                                  authorization_response=request.url)
        user_info = github.get(GITHUB_USERINFO_URL).json()
        return login_or_register_user('github', str(user_info['id']),
                                     user_info.get('name') or user_info.get('login'), user_info.get('email'))
    except:
        flash('فشل تسجيل الدخول بـ GitHub', 'danger')
        return redirect(url_for('login'))

# ========== الصفحة الرئيسية ==========
@app.route('/')
def index():
    posts = get_posts()
    published = [p for p in posts if p.get('published', True)]
    categories = list(set(p.get('category', 'عام') for p in published))
    return render_template('index.html', posts=published, categories=categories)

# ========== عرض مقال ==========
@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = get_post(post_id)
    if not post:
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))

    post['views'] = post.get('views', 0) + 1
    save_post(post_id, post)

    comments = get_comments(post_id)
    user_id = session.get('user_id')
    likes = get_likes(post_id)
    liked = user_id and user_id in likes

    all_posts = get_posts()
    related = [p for p in all_posts if p.get('id') != post_id and p.get('category') == post.get('category') and p.get('published', True)][:3]

    content_html = markdown.markdown(post.get('content', ''), extensions=['fenced_code', 'tables', 'codehilite'])
    return render_template('post.html', post=post, comments=comments,
                          content_html=content_html, liked=liked, related=related,
                          like_count=len(likes))

# ========== تصنيفات ==========
@app.route('/category/<category>')
def category_posts(category):
    posts = get_posts()
    filtered = [p for p in posts if p.get('published', True) and p.get('category') == category]
    return render_template('index.html', posts=filtered, current_category=category)

# ========== بحث ==========
@app.route('/search')
def search():
    query = request.args.get('q', '')
    posts = get_posts()
    if query:
        published = [p for p in posts if p.get('published', True)]
        results = [p for p in published if query.lower() in p.get('title', '').lower() or query.lower() in p.get('content', '').lower()]
    else:
        results = []
    return render_template('index.html', posts=results, search_query=query)

# ========== تعليقات ==========
@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content', '')
    if not content.strip():
        flash('الرجاء كتابة تعليق', 'warning')
        return redirect(url_for('view_post', post_id=post_id))

    comments = get_comments(post_id)
    comments.append({
        'id': len(comments) + 1,
        'author': session.get('username', 'زائر'),
        'content': content,
        'created_at': datetime.now().isoformat()
    })
    save_comments(post_id, comments)
    flash('تم إضافة التعليق بنجاح', 'success')
    return redirect(url_for('view_post', post_id=post_id))

# ========== إعجاب ==========
@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    user_id = session['user_id']
    likes = get_likes(post_id)

    if user_id in likes:
        likes.remove(user_id)
        liked = False
    else:
        likes.append(user_id)
        liked = True

    save_likes(post_id, likes)
    return {'success': True, 'liked': liked, 'count': len(likes)}

# ========== تسجيل الدخول ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = get_users()

        for uid, u in users.items():
            if u['username'] == username and u.get('password') and check_password_hash(u['password'], password):
                session.permanent = True
                session['user_id'] = uid
                session['username'] = u['username']
                session['is_admin'] = u.get('is_admin', False)
                flash(f'مرحباً بك، {username}!', 'success')
                return redirect(url_for('admin' if u.get('is_admin') else 'index'))

        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')

    return render_template('login.html')

# ========== تسجيل ==========
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        users = get_users()

        for u in users.values():
            if u['username'] == username:
                flash('اسم المستخدم موجود بالفعل', 'danger')
                return render_template('register.html')

        uid = str(len(users) + 1)
        users[uid] = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'is_admin': False,
            'bio': '',
            'website': '',
            'avatar_url': '',
            'created_at': datetime.now().isoformat()
        }
        save_users(users)

        session.permanent = True
        session['user_id'] = uid
        session['username'] = username
        session['is_admin'] = False
        flash('تم إنشاء الحساب بنجاح!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

# ========== تسجيل الخروج ==========
@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج', 'success')
    return redirect(url_for('index'))

# ========== لوحة التحكم ==========
@app.route('/admin')
@admin_required
def admin():
    posts = get_posts()
    users = get_users()
    total_comments = 0
    total_likes = 0
    for p in posts:
        total_comments += len(get_comments(p.get('id', 0)))
        total_likes += len(get_likes(p.get('id', 0)))
    return render_template('admin.html', posts=posts,
                          total_posts=len(posts),
                          total_users=len(users),
                          total_comments=total_comments,
                          total_likes=total_likes)

# ========== مقال جديد ==========
@app.route('/new-post', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        post_id = get_next_post_id()
        post = {
            'id': post_id,
            'title': request.form['title'],
            'content': request.form['content'],
            'summary': request.form.get('summary', ''),
            'image_url': request.form.get('image_url', ''),
            'category': request.form.get('category', 'عام'),
            'tags': request.form.get('tags', ''),
            'published': True,
            'views': 0,
            'user_id': session['user_id'],
            'author_name': session.get('username', ''),
            'created_at': datetime.now().isoformat()
        }
        if save_post(post_id, post, 'نشر مقال جديد'):
            flash('تم نشر المقال بنجاح!', 'success')
        else:
            flash('فشل حفظ المقال، تأكد من GITHUB_TOKEN', 'danger')
        return redirect(url_for('my_posts'))

    return render_template('new_post.html')

# ========== منشوراتي ==========
@app.route('/my-posts')
@login_required
def my_posts():
    all_posts = get_posts()
    posts = [p for p in all_posts if str(p.get('user_id')) == str(session['user_id'])]
    return render_template('my_posts.html', posts=posts)

# ========== تعديل مقال ==========
@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = get_post(post_id)
    if not post:
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))

    if str(post.get('user_id')) != str(session['user_id']) and not session.get('is_admin'):
        flash('لا تملك صلاحية تعديل هذا المقال', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        post['title'] = request.form['title']
        post['content'] = request.form['content']
        post['summary'] = request.form.get('summary', '')
        post['image_url'] = request.form.get('image_url', '')
        post['category'] = request.form.get('category', 'عام')
        post['tags'] = request.form.get('tags', '')
        post['published'] = 'published' in request.form
        save_post(post_id, post, 'تحديث مقال')
        flash('تم تحديث المقال بنجاح!', 'success')
        return redirect(url_for('my_posts'))

    return render_template('edit_post.html', post=post)

# ========== حذف مقال ==========
@app.route('/delete-post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = get_post(post_id)
    if not post:
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('index'))

    if str(post.get('user_id')) != str(session['user_id']) and not session.get('is_admin'):
        flash('لا تملك صلاحية حذف هذا المقال', 'danger')
        return redirect(url_for('index'))

    delete_post_file(post_id)
    flash('تم حذف المقال بنجاح', 'success')
    return redirect(url_for('my_posts'))

# ========== الملف الشخصي ==========
@app.route('/profile')
@login_required
def profile():
    users = get_users()
    user = users.get(session['user_id'], {})
    all_posts = get_posts()
    posts_count = len([p for p in all_posts if str(p.get('user_id')) == str(session['user_id'])])
    return render_template('profile.html', user=user, posts_count=posts_count, comments_count=0)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    users = get_users()
    user = users.get(session['user_id'], {})
    if request.method == 'POST':
        user['bio'] = request.form.get('bio', '')
        user['website'] = request.form.get('website', '')
        user['avatar_url'] = request.form.get('avatar_url', '')
        users[session['user_id']] = user
        save_users(users)
        flash('تم تحديث الملف الشخصي', 'success')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', user=user)

@app.route('/user/<username>')
def user_profile(username):
    users = get_users()
    user = None
    uid = None
    for k, v in users.items():
        if v.get('username') == username:
            user = v
            uid = k
            break
    if not user:
        return render_template('404.html'), 404
    all_posts = get_posts()
    posts = [p for p in all_posts if str(p.get('user_id')) == str(uid) and p.get('published', True)]
    return render_template('public_profile.html', user=user, posts=posts, posts_count=len(posts))

# ========== أخطاء ==========
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ========== بدء ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
