"""
منصة مروم FM - الذكاء الاصطناعي المتكامل
جميع الحقوق محفوظة © مروم FM
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
import os
import pg8000
import hashlib
import secrets
from datetime import datetime
from functools import wraps
import requests
import json

# ============================================
# تهيئة التطبيق
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
CORS(app)

# إعدادات API (المتغير البيئي الذي أضفته)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# التحقق من وجود المفتاح
if not GROQ_API_KEY:
    print("⚠️ تحذير: GROQ_API_KEY غير مضبوط في المتغيرات البيئية")

# إعدادات قاعدة البيانات
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
    """تهيئة قاعدة البيانات"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maroom_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maroom_conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES maroom_users(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            model VARCHAR(50) DEFAULT 'llama3-8b-8192',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # مستخدم تجريبي
    cursor.execute("SELECT COUNT(*) FROM maroom_users WHERE username = 'maroom'")
    if cursor.fetchone()[0] == 0:
        demo_pass = hashlib.sha256("maroom123".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO maroom_users (username, email, password_hash)
            VALUES (%s, %s, %s)
        """, ('maroom', 'maroom@maroom.com', demo_pass))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ قاعدة البيانات جاهزة")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def chat_with_groq(messages, model="llama3-8b-8192"):
    """الاتصال بـ Groq API"""
    if not GROQ_API_KEY:
        return "⚠️ عذراً، مفتاح API غير مضبوط. يرجى التواصل مع الدعم الفني."
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ خطأ تقني: {response.status_code}"
    except Exception as e:
        return f"❌ خطأ في الاتصال"

def save_conversation(user_id, role, content):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO maroom_conversations (user_id, role, content)
        VALUES (%s, %s, %s)
    """, (user_id, role, content))
    conn.commit()
    cursor.close()
    conn.close()

def get_conversation_history(user_id, limit=50):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, created_at
        FROM maroom_conversations
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    history = []
    for row in reversed(rows):
        history.append({"role": row[0], "content": row[1], "time": row[2].isoformat() if row[2] else None})
    return history

# ============================================
# القالب الرئيسي (HTML مدمج بالكامل)
# ============================================

MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>مروم FM - منصة الذكاء الاصطناعي</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Cairo', 'Tajawal', 'Segoe UI', sans-serif;
            background: radial-gradient(ellipse at top, #0a0a2a, #050510);
            min-height: 100vh;
            color: #fff;
        }
        
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800&display=swap');
        
        /* شريط التنقل */
        .navbar {
            background: rgba(5, 5, 20, 0.95);
            backdrop-filter: blur(20px);
            padding: 0.8rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            border-bottom: 1px solid rgba(255, 107, 0, 0.3);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        
        .logo {
            font-size: 1.6rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ff6b00, #ff2b7a);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: -0.5px;
        }
        
        .logo span {
            font-size: 0.8rem;
            background: none;
            -webkit-background-clip: unset;
            background-clip: unset;
            color: #ff6b00;
        }
        
        .nav-links {
            display: flex;
            gap: 2rem;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .nav-links a {
            color: #ddd;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .nav-links a:hover {
            color: #ff6b00;
            transform: translateY(-2px);
        }
        
        .logout-btn {
            background: linear-gradient(135deg, #ff2b7a, #ff6b00);
            padding: 0.5rem 1.2rem;
            border-radius: 40px;
            color: white !important;
        }
        
        .logout-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 107, 0, 0.3);
        }
        
        /* الحاوية */
        .container {
            max-width: 1300px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* البطاقات */
        .card {
            background: rgba(20, 20, 50, 0.6);
            backdrop-filter: blur(15px);
            border-radius: 28px;
            padding: 1.8rem;
            margin-bottom: 1.8rem;
            border: 1px solid rgba(255, 107, 0, 0.2);
            transition: all 0.3s;
        }
        
        .card:hover {
            border-color: rgba(255, 107, 0, 0.5);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }
        
        .card h2 {
            background: linear-gradient(90deg, #ff6b00, #ff2b7a);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 1.2rem;
            font-size: 1.6rem;
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }
        
        /* واجهة المحادثة */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 520px;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 20px;
            margin-bottom: 1rem;
        }
        
        .message {
            margin-bottom: 1rem;
            padding: 1rem;
            border-radius: 20px;
            max-width: 85%;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            background: linear-gradient(135deg, #ff6b0022, #ff2b7a22);
            border-right: 3px solid #ff6b00;
            margin-right: auto;
            text-align: right;
        }
        
        .message.assistant {
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid #ff2b7a;
            margin-left: auto;
            text-align: left;
        }
        
        .message-time {
            font-size: 0.7rem;
            color: #888;
            margin-top: 0.5rem;
        }
        
        /* المدخلات */
        .chat-input {
            display: flex;
            gap: 0.8rem;
        }
        
        .chat-input textarea {
            flex: 1;
            padding: 1rem;
            border: 1px solid rgba(255, 107, 0, 0.3);
            border-radius: 20px;
            background: rgba(0, 0, 0, 0.5);
            color: white;
            resize: none;
            font-family: inherit;
            font-size: 1rem;
            transition: all 0.3s;
        }
        
        .chat-input textarea:focus {
            outline: none;
            border-color: #ff6b00;
            box-shadow: 0 0 10px rgba(255, 107, 0, 0.3);
        }
        
        .chat-input button {
            background: linear-gradient(135deg, #ff6b00, #ff2b7a);
            border: none;
            border-radius: 20px;
            padding: 0 2rem;
            cursor: pointer;
            font-weight: bold;
            font-size: 1rem;
            transition: all 0.3s;
        }
        
        .chat-input button:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 20px rgba(255, 107, 0, 0.4);
        }
        
        /* أدوات */
        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }
        
        .tool-btn {
            background: rgba(255, 107, 0, 0.15);
            border: 1px solid rgba(255, 107, 0, 0.4);
            padding: 1rem;
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
            font-weight: 500;
        }
        
        .tool-btn:hover {
            background: rgba(255, 107, 0, 0.3);
            transform: translateY(-3px);
            border-color: #ff6b00;
        }
        
        input, select {
            width: 100%;
            padding: 0.8rem;
            margin: 0.5rem 0;
            border: 1px solid rgba(255, 107, 0, 0.3);
            border-radius: 16px;
            background: rgba(0, 0, 0, 0.5);
            color: white;
            font-size: 1rem;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #ff6b00;
        }
        
        button {
            background: linear-gradient(135deg, #ff6b00, #ff2b7a);
            border: none;
            padding: 0.8rem 1.8rem;
            border-radius: 40px;
            cursor: pointer;
            font-weight: bold;
            font-size: 1rem;
            transition: all 0.3s;
            color: white;
        }
        
        .result-box {
            background: rgba(0, 0, 0, 0.5);
            padding: 1.2rem;
            border-radius: 20px;
            margin-top: 1rem;
            white-space: pre-wrap;
            line-height: 1.6;
            border: 1px solid rgba(255, 107, 0, 0.3);
        }
        
        /* التنبيهات */
        .alert {
            padding: 1rem;
            border-radius: 16px;
            margin-bottom: 1rem;
        }
        
        .alert-success {
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            color: #00ff00;
        }
        
        .alert-error {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid #ff4444;
            color: #ff4444;
        }
        
        /* التذييل */
        .footer {
            text-align: center;
            padding: 1.5rem;
            background: rgba(0, 0, 0, 0.5);
            margin-top: 2rem;
            font-size: 0.8rem;
            color: #666;
        }
        
        /* استجابة */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            .navbar {
                flex-direction: column;
                text-align: center;
            }
            .message {
                max-width: 95%;
            }
        }
        
        /* شريط التمرير */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #1a1a3a;
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb {
            background: #ff6b00;
            border-radius: 10px;
        }
        
        /* تأثيرات إضافية */
        .glow-text {
            text-shadow: 0 0 10px rgba(255, 107, 0, 0.5);
        }
        
        .hero-badge {
            display: inline-block;
            background: rgba(255, 107, 0, 0.2);
            padding: 0.3rem 1rem;
            border-radius: 40px;
            font-size: 0.8rem;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">
            🎙️ مروم FM <span>AI</span>
        </div>
        <div class="nav-links">
            <a href="{{ url_for('index') }}">💬 المحادثة</a>
            <a href="{{ url_for('tools') }}">🛠️ أدوات الذكاء</a>
            <a href="{{ url_for('history') }}">📜 السجل</a>
            <a href="{{ url_for('logout') }}" class="logout-btn">🚪 خروج</a>
        </div>
    </nav>
    
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
    
    <div class="footer">
        <p>© 2026 مروم FM - جميع الحقوق محفوظة | ذكاء اصطناعي متقدم</p>
    </div>
</body>
</html>
'''

CHAT_SECTION = '''
<div class="card">
    <h2>💬 محادثة ذكية</h2>
    <p style="margin-bottom: 1rem; opacity: 0.8;">🎙️ تحدث مع ذكاء مروم FM الاصطناعي</p>
    
    <div class="chat-container">
        <div class="chat-messages" id="chatMessages">
            {% for msg in history %}
            <div class="message {{ msg.role }}">
                <strong>{{ '👤 أنت' if msg.role == 'user' else '🎙️ مروم FM' }}</strong>
                <p>{{ msg.content }}</p>
                <div class="message-time">{{ msg.time[:16] if msg.time else '' }}</div>
            </div>
            {% endfor %}
        </div>
        
        <div class="chat-input">
            <textarea id="messageInput" rows="2" placeholder="اكتب رسالتك هنا..."></textarea>
            <button onclick="sendMessage()">إرسال ➤</button>
        </div>
    </div>
</div>

<div class="card">
    <h2>⚙️ إعدادات المحادثة</h2>
    <select id="modelSelect">
        <option value="llama3-8b-8192">🦙 نموذج مروم FM السريع</option>
        <option value="mixtral-8x7b-32768">🧠 نموذج مروم FM المتقدم</option>
        <option value="gemma2-9b-it">⚡ نموذج مروم FM المتوازن</option>
    </select>
    <button onclick="clearChat()" style="background: rgba(255,0,0,0.3); margin-top:0.5rem;">🗑️ مسح المحادثة</button>
</div>

<script>
    function sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        if (!message) return;
        
        const model = document.getElementById('modelSelect').value;
        
        const messagesDiv = document.getElementById('chatMessages');
        const userMsg = document.createElement('div');
        userMsg.className = 'message user';
        userMsg.innerHTML = '<strong>👤 أنت</strong><p>' + escapeHtml(message) + '</p>';
        messagesDiv.appendChild(userMsg);
        
        input.value = '';
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        const loadingMsg = document.createElement('div');
        loadingMsg.className = 'message assistant';
        loadingMsg.id = 'loadingMsg';
        loadingMsg.innerHTML = '<strong>🎙️ مروم FM</strong><p>🤔 جاري التفكير...</p>';
        messagesDiv.appendChild(loadingMsg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        fetch('/chat/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: message, model: model})
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loadingMsg').remove();
            const aiMsg = document.createElement('div');
            aiMsg.className = 'message assistant';
            aiMsg.innerHTML = '<strong>🎙️ مروم FM</strong><p>' + escapeHtml(data.reply) + '</p>';
            messagesDiv.appendChild(aiMsg);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        })
        .catch(error => {
            document.getElementById('loadingMsg').remove();
            const errorMsg = document.createElement('div');
            errorMsg.className = 'message assistant';
            errorMsg.innerHTML = '<strong>🎙️ مروم FM</strong><p>❌ عذراً، حدث خطأ تقني</p>';
            messagesDiv.appendChild(errorMsg);
        });
    }
    
    function clearChat() {
        if(confirm('هل تريد مسح المحادثة الحالية؟')) {
            fetch('/chat/clear', {method: 'POST'})
            .then(() => window.location.reload());
        }
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    document.getElementById('messageInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
</script>
'''

TOOLS_SECTION = '''
<div class="card">
    <h2>🛠️ أدوات مروم FM الذكية</h2>
    <p style="margin-bottom: 1rem; opacity: 0.8;">تحليل، ترجمة، تدقيق، وإبداع</p>
    <div class="tools-grid">
        <div class="tool-btn" onclick="analyze('summary')">📝 تلخيص ذكي</div>
        <div class="tool-btn" onclick="analyze('translate')">🌐 ترجمة فورية</div>
        <div class="tool-btn" onclick="analyze('grammar')">✍️ تدقيق لغوي</div>
        <div class="tool-btn" onclick="analyze('sentiment')">😊 تحليل المشاعر</div>
        <div class="tool-btn" onclick="analyze('code')">💻 شرح أكواد</div>
        <div class="tool-btn" onclick="analyze('ideas')">💡 توليد أفكار</div>
    </div>
    
    <textarea id="toolInput" rows="5" placeholder="أدخل النص هنا..." style="width:100%; margin:1rem 0;"></textarea>
    <button onclick="runTool()">تنفيذ ➤</button>
    
    <div id="toolResult" class="result-box"></div>
</div>

<script>
    let currentAction = 'summary';
    
    function analyze(action) {
        currentAction = action;
        const actions = {
            'summary': 'قم بتلخيص النص التالي بشكل احترافي وموجز:',
            'translate': 'ترجم النص التالي إلى اللغة العربية الفصحى:',
            'grammar': 'صحح الأخطاء الإملائية والنحوية في النص التالي:',
            'sentiment': 'حلل المشاعر في النص التالي وأجب بإيجابي أو سلبي أو محايد:',
            'code': 'اشرح الكود التالي بطريقة مبسطة للمبتدئين:',
            'ideas': 'اقترح 5 أفكار إبداعية مبتكرة بناءً على النص التالي:'
        };
        
        document.getElementById('toolInput').placeholder = actions[action];
        document.querySelectorAll('.tool-btn').forEach(btn => btn.style.background = 'rgba(255,107,0,0.15)');
        event.target.style.background = 'rgba(255,107,0,0.4)';
    }
    
    function runTool() {
        const text = document.getElementById('toolInput').value;
        if (!text) {
            alert('الرجاء إدخال نص');
            return;
        }
        
        document.getElementById('toolResult').innerHTML = '<p>🤔 جاري المعالجة...</p>';
        
        fetch('/tool/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action: currentAction, text: text})
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('toolResult').innerHTML = '<p><strong>النتيجة:</strong></p><p>' + data.result.replace(/\\n/g, '<br>') + '</p>';
        })
        .catch(error => {
            document.getElementById('toolResult').innerHTML = '<p>❌ عذراً، حدث خطأ تقني</p>';
        });
    }
    
    analyze('summary');
</script>
'''

HISTORY_SECTION = '''
<div class="card">
    <h2>📜 سجل المحادثات</h2>
    <p style="margin-bottom: 1rem; opacity: 0.8;">جميع محادثاتك مع مروم FM</p>
    {% if history %}
        {% for msg in history %}
        <div class="message {{ msg.role }}" style="max-width:100%; margin-bottom:1rem;">
            <strong>{{ '👤 أنت' if msg.role == 'user' else '🎙️ مروم FM' }}</strong>
            <p>{{ msg.content[:300] }}{% if msg.content|length > 300 %}...{% endif %}</p>
            <div class="message-time">{{ msg.time[:16] if msg.time else '' }}</div>
        </div>
        {% endfor %}
    {% else %}
        <p>📭 لا توجد محادثات سابقة. ابدأ محادثة جديدة!</p>
    {% endif %}
</div>
'''

# ============================================
# المسارات
# ============================================

@app.route('/')
@login_required
def index():
    history = get_conversation_history(session['user_id'], 50)
    return render_template_string(MAIN_TEMPLATE + CHAT_SECTION, history=history)

@app.route('/tools')
@login_required
def tools():
    return render_template_string(MAIN_TEMPLATE + TOOLS_SECTION)

@app.route('/history')
@login_required
def history():
    history = get_conversation_history(session['user_id'], 100)
    return render_template_string(MAIN_TEMPLATE + HISTORY_SECTION, history=history)

@app.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    data = request.get_json()
    user_message = data.get('message', '')
    model = data.get('model', 'llama3-8b-8192')
    
    save_conversation(session['user_id'], 'user', user_message)
    
    history = get_conversation_history(session['user_id'], 10)
    messages = []
    for msg in history:
        messages.append({"role": msg['role'], "content": msg['content']})
    messages.append({"role": "user", "content": user_message})
    
    reply = chat_with_groq(messages, model)
    save_conversation(session['user_id'], 'assistant', reply)
    
    return jsonify({"reply": reply})

@app.route('/chat/clear', methods=['POST'])
@login_required
def chat_clear():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM maroom_conversations WHERE user_id = %s", (session['user_id'],))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/tool/run', methods=['POST'])
@login_required
def tool_run():
    data = request.get_json()
    action = data.get('action')
    text = data.get('text')
    
    prompts = {
        'summary': f"قم بتلخيص النص التالي بشكل احترافي وموجز مع الحفاظ على المعنى:\n\n{text}",
        'translate': f"ترجم النص التالي إلى اللغة العربية الفصحى بدقة:\n\n{text}",
        'grammar': f"صحح الأخطاء الإملائية والنحوية في النص التالي وأعد كتابته بشكل صحيح:\n\n{text}",
        'sentiment': f"حلل المشاعر في النص التالي وحدد هل هو إيجابي أم سلبي أم محايد مع شرح السبب:\n\n{text}",
        'code': f"اشرح الكود التالي بطريقة مبسطة للمبتدئين مع ذكر وظيفته:\n\n{text}",
        'ideas': f"اقترح 5 أفكار إبداعية ومبتكرة بناءً على النص التالي مع شرح كل فكرة:\n\n{text}"
    }
    
    messages = [{"role": "user", "content": prompts.get(action, prompts['summary'])}]
    result = chat_with_groq(messages)
    
    return jsonify({"result": result})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash FROM maroom_users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and user[2] == hash_password(password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('مرحباً بك في مروم FM!', 'success')
            return redirect(url_for('index'))
        
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مروم FM - تسجيل الدخول</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box}
            body{
                font-family:'Cairo','Tajawal',sans-serif;
                background:radial-gradient(ellipse at top,#0a0a2a,#050510);
                display:flex;
                justify-content:center;
                align-items:center;
                min-height:100vh;
            }
            .login-card{
                background:rgba(20,20,50,0.8);
                backdrop-filter:blur(20px);
                padding:2.5rem;
                border-radius:40px;
                width:100%;
                max-width:420px;
                text-align:center;
                border:1px solid rgba(255,107,0,0.3);
                animation:fadeIn 0.5s ease;
            }
            @keyframes fadeIn{from{opacity:0;transform:translateY(-20px)}to{opacity:1;transform:translateY(0)}}
            h1{
                font-size:2.2rem;
                background:linear-gradient(135deg,#ff6b00,#ff2b7a);
                -webkit-background-clip:text;
                background-clip:text;
                color:transparent;
                margin-bottom:0.5rem;
            }
            .sub{color:#888;margin-bottom:1.5rem;font-size:0.9rem}
            input{
                width:100%;
                padding:1rem;
                margin:0.7rem 0;
                border:1px solid rgba(255,107,0,0.3);
                border-radius:60px;
                background:rgba(0,0,0,0.5);
                color:white;
                font-size:1rem;
                transition:0.3s;
            }
            input:focus{outline:none;border-color:#ff6b00}
            button{
                width:100%;
                background:linear-gradient(135deg,#ff6b00,#ff2b7a);
                border:none;
                padding:1rem;
                border-radius:60px;
                cursor:pointer;
                font-weight:bold;
                font-size:1rem;
                margin-top:1rem;
                transition:0.3s;
            }
            button:hover{transform:scale(1.02);box-shadow:0 5px 20px rgba(255,107,0,0.4)}
            .demo-info{
                margin-top:1.5rem;
                padding:0.8rem;
                background:rgba(255,107,0,0.1);
                border-radius:20px;
                font-size:0.8rem;
                color:#ff6b00;
            }
            .alert{padding:0.8rem;border-radius:20px;margin-bottom:1rem;font-size:0.9rem}
            .alert-success{background:rgba(0,255,0,0.1);border:1px solid #00ff00;color:#00ff00}
            .alert-error{background:rgba(255,0,0,0.1);border:1px solid #ff4444;color:#ff4444}
        </style>
    </head>
    <body>
        <div class="login-card">
            <h1>🎙️ مروم FM</h1>
            <div class="sub">منصة الذكاء الاصطناعي المتكاملة</div>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endwith %}
            <form method="POST">
                <input type="text" name="username" placeholder="اسم المستخدم" required>
                <input type="password" name="password" placeholder="كلمة المرور" required>
                <button type="submit">دخول</button>
            </form>
            <div class="demo-info">
                🔑 تجريبي: maroom / maroom123
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    print("🎙️ بدء تشغيل منصة مروم FM للذكاء الاصطناعي...")
    init_db()
    print("✅ قاعدة البيانات جاهزة")
    print(f"🔑 مفتاح API: {'موجود ✅' if GROQ_API_KEY else 'غير موجود ❌'}")
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
