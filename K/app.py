"""
نبض الحدث - مدونة عصرية متكاملة مع دعم القوالب المنفصلة
للرفع على Render.com
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
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
                  views INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT,
                  password_hash TEXT NOT NULL,
                  is_admin BOOLEAN DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
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
        c.execute("INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
                 ('admin', 'admin@example.com', generate_password_hash('admin123')))
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

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
        if 'user_id' not in session or not session.get('is_admin'):
            flash('صلاحيات غير كافية', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

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
    
    categories = db.execute('SELECT DISTINCT category FROM posts WHERE published = 1').fetchall()
    db.close()
    return render_template('index.html', posts=posts, categories=categories)

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
    
    # زيادة المشاهدات
    db.execute('UPDATE posts SET views = views + 1 WHERE id = ?', (post_id,))
    
    comments = db.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY created_at DESC', (post_id,)).fetchall()
    ip = request.remote_addr
    liked = db.execute('SELECT id FROM likes WHERE post_id = ? AND ip_address = ?', (post_id, ip)).fetchone()
    related = db.execute('SELECT * FROM posts WHERE category = ? AND id != ? AND published = 1 LIMIT 3', 
                        (post['category'], post_id)).fetchall()
    
    db.commit()
    db.close()
    
    # تحويل Markdown إلى HTML
    content_html = markdown.markdown(post['content'], extensions=['fenced_code', 'tables', 'codehilite'])
    
    return render_template('post.html', post=post, comments=comments, 
                          content_html=content_html, liked=liked is not None, related=related)

@app.route('/category/<category>')
def category_posts(category):
    db = get_db()
    posts = db.execute('SELECT * FROM posts WHERE category = ? AND published = 1 ORDER BY created_at DESC', 
                      (category,)).fetchall()
    db.close()
    return render_template('index.html', posts=posts, current_category=category)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        db = get_db()
        posts = db.execute('''
            SELECT * FROM posts 
            WHERE published = 1 
            AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)
            ORDER BY created_at DESC
        ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
        db.close()
    else:
        posts = []
    return render_template('index.html', posts=posts, search_query=query)

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
    
    existing = db.execute('SELECT id FROM likes WHERE post_id = ? AND ip_address = ?', 
                         (post_id, ip)).fetchone()
    
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
            flash(f'مرحباً بك، {user["username"]}!', 'success')
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
        db.close()
        
        flash('تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('login'))
    
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
    posts = db.execute('SELECT * FROM posts ORDER BY created_at DESC').fetchall()
    total_posts = len(posts)
    total_comments = db.execute('SELECT COUNT(*) as count FROM comments').fetchone()['count']
    total_likes = db.execute('SELECT COUNT(*) as count FROM likes').fetchone()['count']
    db.close()
    return render_template('admin.html', posts=posts, total_posts=total_posts, 
                          total_comments=total_comments, total_likes=total_likes)

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
    
    return render_template('new_post.html')

@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@admin_required
def edit_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if not post:
        db.close()
        flash('المقال غير موجود', 'danger')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        summary = request.form.get('summary', '')
        image_url = request.form.get('image_url', '')
        category = request.form.get('category', 'عام')
        tags = request.form.get('tags', '')
        published = 'published' in request.form
        
        db.execute('''UPDATE posts 
                     SET title=?, content=?, summary=?, image_url=?, category=?, tags=?, published=?
                     WHERE id=?''',
                  (title, content, summary, image_url, category, tags, published, post_id))
        db.commit()
        db.close()
        
        flash('تم تحديث المقال بنجاح!', 'success')
        return redirect(url_for('admin'))
    
    db.close()
    return render_template('edit_post.html', post=post)

@app.route('/delete-post/<int:post_id>')
@admin_required
def delete_post(post_id):
    db = get_db()
    db.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM likes WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.commit()
    db.close()
    
    flash('تم حذف المقال وجميع التعليقات والإعجابات المرتبطة به', 'success')
    return redirect(url_for('admin'))

# ========== معالجة الأخطاء ==========
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ========== بدء التطبيق ==========
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)