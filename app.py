"""
مروم FM AI - منصة ذكاء اصطناعي متكاملة
تخزين المحادثات في localStorage للمتصفح
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime
from functools import wraps

# ============================================
# تهيئة التطبيق
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'maroom-secret-key-2026')
CORS(app)

# إعدادات Groq API
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ============================================
# الدوال المساعدة
# ============================================

def chat_with_groq(message, model="llama-3.3-70b-versatile"):
    """الاتصال بـ Groq API"""
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith('gsk_'):
        return "⚠️ مفتاح Groq غير مضبوط"
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"⚠️ خطأ: {response.status_code}"
    except Exception as e:
        return f"⚠️ خطأ: {str(e)[:100]}"

# ============================================
# إدارة مفاتيح API للتطبيقات الخارجية
# ============================================

ALLOWED_APPS = {
    "android_app": {
        "api_key": "maroom_android_2026_secret_key_1",
        "name": "📱 تطبيق أندرويد مروم FM",
        "rate_limit": 1000
    },
    "web_app": {
        "api_key": "maroom_web_2026_secret_key_2", 
        "name": "💻 موقع مروم FM",
        "rate_limit": 500
    },
    "test_app": {
        "api_key": "maroom_test_2026_secret_key_3",
        "name": "🧪 تطبيق تجريبي",
        "rate_limit": 100
    }
}

request_counts = {}

def verify_api_key(api_key):
    for app_id, app_data in ALLOWED_APPS.items():
        if app_data["api_key"] == api_key:
            return app_id, app_data
    return None, None

def check_rate_limit(app_id, api_key):
    current_hour = datetime.now().strftime("%Y-%m-%d-%H")
    key = f"{app_id}:{api_key}:{current_hour}"
    
    if key not in request_counts:
        request_counts[key] = 0
    
    limit = ALLOWED_APPS[app_id]["rate_limit"]
    
    if request_counts[key] >= limit:
        return False, limit
    
    request_counts[key] += 1
    return True, limit

def api_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({"error": "مطلوب مفتاح API"}), 401
        
        app_id, app_data = verify_api_key(api_key)
        
        if not app_id:
            return jsonify({"error": "مفتاح API غير صالح"}), 401
        
        allowed, limit = check_rate_limit(app_id, api_key)
        if not allowed:
            return jsonify({"error": "تم تجاوز حد الطلبات", "limit": limit}), 429
        
        request.app_info = app_data
        request.app_id = app_id
        return f(*args, **kwargs)
    return decorated

# ============================================
# قالب HTML الرئيسي
# ============================================

MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مروم FM AI - ذكاء اصطناعي متقدم</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg: #0a0a2a;
            --card: #1a1a3a;
            --text: #fff;
            --text-sec: #aaa;
            --primary: #ff6b00;
            --secondary: #ff2b7a;
            --input: #0f0f2a;
        }
        
        [data-theme="light"] {
            --bg: #f0f2f5;
            --card: #ffffff;
            --text: #1a1a2e;
            --text-sec: #666;
            --primary: #ff6b00;
            --secondary: #ff2b7a;
            --input: #e8e8ec;
        }
        
        body {
            font-family: 'Cairo', 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        
        .navbar {
            background: var(--card);
            padding: 0.8rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--primary);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            font-size: 1.3rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        
        .menu-btn {
            background: none;
            border: none;
            font-size: 1.8rem;
            cursor: pointer;
            color: var(--text);
        }
        
        .sidebar {
            position: fixed;
            top: 0;
            right: -280px;
            width: 280px;
            height: 100%;
            background: var(--card);
            z-index: 1000;
            transition: 0.3s;
            padding: 1.5rem;
            overflow-y: auto;
            box-shadow: -5px 0 20px rgba(0,0,0,0.3);
        }
        
        .sidebar.open { right: 0; }
        
        .sidebar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--primary);
        }
        
        .close-menu {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text);
        }
        
        .sidebar-section {
            margin-bottom: 1.8rem;
        }
        
        .sidebar-section h3 {
            color: var(--primary);
            margin-bottom: 0.8rem;
            font-size: 1rem;
        }
        
        .sidebar-item {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            padding: 0.7rem;
            border-radius: 12px;
            cursor: pointer;
            transition: 0.3s;
        }
        
        .sidebar-item:hover {
            background: rgba(255, 107, 0, 0.2);
        }
        
        .theme-toggle {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.7rem;
            background: var(--input);
            border-radius: 40px;
            cursor: pointer;
        }
        
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 999;
            display: none;
        }
        
        .overlay.active { display: block; }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 1.5rem;
        }
        
        .card {
            background: var(--card);
            border-radius: 24px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 107, 0, 0.3);
        }
        
        .card h2 {
            color: var(--primary);
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }
        
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 500px;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            background: var(--input);
            border-radius: 20px;
            margin-bottom: 1rem;
        }
        
        .message {
            margin-bottom: 1rem;
            padding: 0.8rem 1rem;
            border-radius: 18px;
            max-width: 85%;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            background: linear-gradient(135deg, var(--primary)22, var(--secondary)22);
            border-right: 3px solid var(--primary);
            margin-right: auto;
            text-align: right;
        }
        
        .message.assistant {
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid var(--secondary);
            margin-left: auto;
            text-align: left;
        }
        
        .message-time {
            font-size: 0.7rem;
            color: var(--text-sec);
            margin-top: 0.3rem;
        }
        
        .chat-input {
            display: flex;
            gap: 0.8rem;
        }
        
        .chat-input textarea {
            flex: 1;
            padding: 0.8rem;
            border: 1px solid rgba(255, 107, 0, 0.3);
            border-radius: 20px;
            background: var(--input);
            color: var(--text);
            resize: none;
            font-family: inherit;
        }
        
        .chat-input textarea:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .chat-input button {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 20px;
            padding: 0 1.5rem;
            cursor: pointer;
            font-weight: bold;
            color: white;
            transition: transform 0.2s;
        }
        
        .chat-input button:hover {
            transform: scale(1.02);
        }
        
        .history-item {
            background: var(--input);
            padding: 0.8rem;
            border-radius: 12px;
            margin-bottom: 0.5rem;
            border-right: 2px solid var(--primary);
        }
        
        .history-question {
            color: var(--primary);
            font-weight: bold;
            font-size: 0.85rem;
        }
        
        .history-answer {
            color: var(--text-sec);
            margin-top: 0.3rem;
            font-size: 0.8rem;
        }
        
        .history-time {
            font-size: 0.6rem;
            color: #555;
            margin-top: 0.3rem;
        }
        
        .footer {
            text-align: center;
            padding: 1rem;
            color: var(--text-sec);
            font-size: 0.7rem;
        }
        
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .message { max-width: 95%; }
        }
        
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: var(--input); }
        ::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 10px; }
        
        .clear-btn {
            background: rgba(220, 53, 69, 0.8);
            border: none;
            border-radius: 8px;
            padding: 0.3rem 0.8rem;
            color: white;
            cursor: pointer;
            font-size: 0.7rem;
            margin-right: 0.5rem;
        }
        
        .clear-btn:hover { background: #dc3545; }
    </style>
</head>
<body>
    <div class="overlay" id="overlay"></div>
    
    <nav class="navbar">
        <button class="menu-btn" id="menuBtn">☰</button>
        <div class="logo">🎙️ مروم FM AI</div>
        <div style="width: 40px;"></div>
    </nav>
    
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h3>⚙️ القائمة</h3>
            <button class="close-menu" id="closeMenu">✕</button>
        </div>
        
        <div class="sidebar-section">
            <h3>🎨 المظهر</h3>
            <div class="theme-toggle" id="themeToggle">
                <span>🌙 ليلي</span>
                <span>☀️ نهاري</span>
            </div>
        </div>
        
        <div class="sidebar-section">
            <h3>📱 أقسام التطبيق</h3>
            <div class="sidebar-item" onclick="showTab('chat')">
                <span>💬</span> <span>المحادثة</span>
            </div>
            <div class="sidebar-item" onclick="showTab('history')">
                <span>📜</span> <span>سجل المحادثات</span>
            </div>
            <div class="sidebar-item" onclick="window.open('/api/docs', '_blank')">
                <span>🔌</span> <span>توثيق API</span>
            </div>
        </div>
        
        <div class="sidebar-section">
            <h3>⚡ إعدادات</h3>
            <div class="sidebar-item" onclick="clearAllHistory()">
                <span>🗑️</span> <span>مسح كل المحادثات</span>
            </div>
            <div class="sidebar-item" onclick="window.location.reload()">
                <span>🔄</span> <span>تحديث الصفحة</span>
            </div>
        </div>
        
        <div class="sidebar-section">
            <h3>ℹ️ معلومات</h3>
            <div class="sidebar-item">
                <span>🎙️</span> <span>مروم FM AI v3.0</span>
            </div>
            <div class="sidebar-item">
                <span>💾</span> <span>التخزين: محلي</span>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- تبويب المحادثة -->
        <div id="chatTab" class="tab-content">
            <div class="card">
                <h2>💬 محادثة ذكية مع مروم FM AI</h2>
                <div class="chat-container">
                    <div class="chat-messages" id="chatMessages"></div>
                    <div class="chat-input">
                        <textarea id="messageInput" rows="2" placeholder="اكتب رسالتك هنا..."></textarea>
                        <button onclick="sendMessage()">إرسال ➤</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- تبويب سجل المحادثات -->
        <div id="historyTab" class="tab-content" style="display:none;">
            <div class="card">
                <h2>📜 سجل المحادثات <button class="clear-btn" onclick="clearAllHistory()">مسح الكل</button></h2>
                <div id="historyList"></div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>© 2026 مروم FM AI - جميع الحقوق محفوظة | مدعوم من Groq AI | التخزين في متصفحك</p>
    </div>
    
    <script>
        // ============================================
        // إدارة التخزين المحلي (localStorage)
        // ============================================
        
        const STORAGE_KEY = 'maroom_chat_history';
        
        function getSessionId() {
            let sessionId = localStorage.getItem('maroom_session_id');
            if (!sessionId) {
                sessionId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 8);
                localStorage.setItem('maroom_session_id', sessionId);
            }
            return sessionId;
        }
        
        function getHistory() {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                return JSON.parse(stored);
            }
            return [];
        }
        
        function saveHistory(history) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
        }
        
        function addMessageToHistory(role, content) {
            const history = getHistory();
            history.push({
                role: role,
                content: content,
                time: new Date().toISOString()
            });
            saveHistory(history);
            
            // تحديث واجهة السجل إذا كانت مفتوحة
            if (document.getElementById('historyTab').style.display !== 'none') {
                displayHistory();
            }
        }
        
        function clearAllHistory() {
            if (confirm('⚠️ هل أنت متأكد من مسح كل المحادثات؟ لا يمكن التراجع.')) {
                localStorage.removeItem(STORAGE_KEY);
                displayMessages();
                displayHistory();
                if (document.getElementById('historyTab').style.display !== 'none') {
                    document.getElementById('historyList').innerHTML = '<p style="text-align:center;color:#888;">📭 لا توجد محادثات سابقة</p>';
                }
            }
        }
        
        function displayMessages() {
            const history = getHistory();
            const container = document.getElementById('chatMessages');
            
            if (history.length === 0) {
                container.innerHTML = '<div class="message assistant"><strong>🎙️ مروم FM AI</strong><p>مرحباً بك! أنا مساعدك الذكي. كيف يمكنني مساعدتك اليوم؟</p><div class="message-time">الآن</div></div>';
                return;
            }
            
            container.innerHTML = history.map(msg => `
                <div class="message ${msg.role}">
                    <strong>${msg.role === 'user' ? '👤 أنت' : '🎙️ مروم FM AI'}</strong>
                    <p>${escapeHtml(msg.content)}</p>
                    <div class="message-time">${formatTime(msg.time)}</div>
                </div>
            `).join('');
            
            container.scrollTop = container.scrollHeight;
        }
        
        function displayHistory() {
            const history = getHistory();
            const container = document.getElementById('historyList');
            
            if (history.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#888;">📭 لا توجد محادثات سابقة</p>';
                return;
            }
            
            // عرض المحادثات مجمعة (سؤال + جواب)
            const grouped = [];
            for (let i = 0; i < history.length; i += 2) {
                if (history[i].role === 'user') {
                    grouped.push({
                        question: history[i],
                        answer: history[i + 1] || null
                    });
                }
            }
            
            container.innerHTML = grouped.map(g => `
                <div class="history-item">
                    <div class="history-question">👤 ${escapeHtml(g.question.content)}</div>
                    ${g.answer ? `<div class="history-answer">🎙️ ${escapeHtml(g.answer.content)}</div>` : ''}
                    <div class="history-time">${formatTime(g.question.time)}</div>
                </div>
            `).join('');
        }
        
        function formatTime(isoString) {
            if (!isoString) return 'الآن';
            const date = new Date(isoString);
            return date.toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // ============================================
        // دوال المحادثة
        // ============================================
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;
            
            // إضافة رسالة المستخدم للواجهة والتاريخ
            addMessageToHistory('user', message);
            displayMessages();
            
            input.value = '';
            
            // إظهار مؤشر التحميل
            const container = document.getElementById('chatMessages');
            const loadingId = 'loading_' + Date.now();
            container.innerHTML += `
                <div class="message assistant" id="${loadingId}">
                    <strong>🎙️ مروم FM AI</strong>
                    <p>🤔 جاري التفكير مع Groq...</p>
                    <div class="message-time">الآن</div>
                </div>
            `;
            container.scrollTop = container.scrollHeight;
            
            try {
                const sessionId = getSessionId();
                const response = await fetch('/chat/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message, sessionId: sessionId })
                });
                const data = await response.json();
                
                // إزالة مؤشر التحميل
                document.getElementById(loadingId)?.remove();
                
                // إضافة رد الذكاء للواجهة والتاريخ
                addMessageToHistory('assistant', data.reply);
                displayMessages();
                
            } catch (error) {
                document.getElementById(loadingId)?.remove();
                addMessageToHistory('assistant', '❌ عذراً، حدث خطأ تقني. حاول مرة أخرى.');
                displayMessages();
            }
        }
        
        function showTab(tab) {
            document.getElementById('chatTab').style.display = 'none';
            document.getElementById('historyTab').style.display = 'none';
            
            if (tab === 'chat') {
                document.getElementById('chatTab').style.display = 'block';
                displayMessages();
            }
            if (tab === 'history') {
                document.getElementById('historyTab').style.display = 'block';
                displayHistory();
            }
            closeSidebar();
        }
        
        // ============================================
        // القائمة الجانبية
        // ============================================
        
        const menuBtn = document.getElementById('menuBtn');
        const sidebar = document.getElementById('sidebar');
        const closeMenu = document.getElementById('closeMenu');
        const overlay = document.getElementById('overlay');
        
        function openSidebar() { sidebar.classList.add('open'); overlay.classList.add('active'); }
        function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('active'); }
        
        menuBtn.onclick = openSidebar;
        closeMenu.onclick = closeSidebar;
        overlay.onclick = closeSidebar;
        
        // ============================================
        // الوضع الليلي والنهاري
        // ============================================
        
        const themeToggle = document.getElementById('themeToggle');
        if (localStorage.getItem('theme') === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        }
        
        themeToggle.onclick = () => {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        };
        
        // ============================================
        // إرسال بالضغط على Enter
        // ============================================
        
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // ============================================
        // التحميل الأولي
        // ============================================
        
        displayMessages();
    </script>
</body>
</html>
'''

# ============================================
# المسارات الأساسية
# ============================================

@app.route('/')
def index():
    return render_template_string(MAIN_TEMPLATE)

@app.route('/chat/send', methods=['POST'])
def chat_send():
    data = request.get_json()
    message = data.get('message', '')
    session_id = data.get('sessionId', 'default')
    
    if not message:
        return jsonify({"reply": "الرجاء كتابة رسالة"}), 200
    
    reply = chat_with_groq(message)
    return jsonify({"reply": reply})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "مروم FM AI", "storage": "localStorage"}), 200

# ============================================
# نقاط API للتطبيقات الخارجية
# ============================================

@app.route('/api/v1/chat', methods=['POST'])
@api_required
def api_v1_chat():
    data = request.get_json()
    message = data.get('message', '')
    session_id = data.get('session_id', f"api_{request.app_id}_{datetime.now().timestamp()}")
    
    if not message:
        return jsonify({"error": "الرسالة مطلوبة"}), 400
    
    reply = chat_with_groq(message)
    
    return jsonify({
        "success": True,
        "reply": reply,
        "session_id": session_id,
        "app": request.app_info['name'],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/health', methods=['GET'])
@api_required
def api_v1_health():
    return jsonify({
        "status": "healthy",
        "service": "مروم FM AI",
        "version": "3.0.0",
        "app": request.app_info['name'],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/docs')
def api_docs():
    docs_html = '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مروم FM AI - توثيق API</title>
        <style>
            body { font-family: 'Cairo', sans-serif; background: #0a0a2a; color: #fff; padding: 2rem; }
            .container { max-width: 900px; margin: 0 auto; }
            .card { background: #1a1a3a; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; border-right: 4px solid #ff6b00; }
            h1 { color: #ff6b00; }
            h2 { color: #ff2b7a; font-size: 1.2rem; margin-top: 1rem; }
            code { background: #0f0f2a; padding: 0.2rem 0.5rem; border-radius: 8px; font-family: monospace; }
            pre { background: #0f0f2a; padding: 1rem; border-radius: 12px; overflow-x: auto; }
            .badge { display: inline-block; background: #28a745; padding: 0.2rem 0.8rem; border-radius: 20px; font-size: 0.7rem; margin-left: 0.5rem; }
            .badge-post { background: #007bff; }
            .badge-get { background: #28a745; }
            .badge-delete { background: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔌 مروم FM AI - توثيق API</h1>
            <p>لربط تطبيقات APK والمواقع مع خادم مروم FM AI</p>
            
            <div class="card">
                <h2>🔑 الحصول على مفتاح API</h2>
                <p>المفاتيح المتاحة حالياً:</p>
                <ul>
                    <li><strong>تطبيق أندرويد</strong>: <code>maroom_android_2026_secret_key_1</code></li>
                    <li><strong>موقع الويب</strong>: <code>maroom_web_2026_secret_key_2</code></li>
                    <li><strong>تطبيق تجريبي</strong>: <code>maroom_test_2026_secret_key_3</code></li>
                </ul>
            </div>
            
            <div class="card">
                <h2>📡 نقاط النهاية</h2>
                
                <h3><span class="badge badge-post">POST</span> /api/v1/chat</h3>
                <p>إرسال رسالة والحصول على رد من الذكاء الاصطناعي.</p>
                <pre>{
  "message": "مرحباً",
  "session_id": "user_123"
}</pre>
                
                <h3><span class="badge badge-get">GET</span> /api/v1/health</h3>
                <p>فحص صحة الخادم.</p>
                
                <h3><span class="badge badge-get">GET</span> /api/docs</h3>
                <p>هذه الصفحة.</p>
            </div>
            
            <div class="card">
                <h2>🐍 مثال باستخدام Python</h2>
                <pre>
import requests

url = "https://kruri.qzz.io/api/v1/chat"
headers = {"X-API-Key": "maroom_android_2026_secret_key_1"}
data = {"message": "ما هو الذكاء الاصطناعي?"}

response = requests.post(url, json=data, headers=headers)
print(response.json())
                </pre>
            </div>
        </div>
    </body>
    </html>
    '''
    return docs_html

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("🎙️ بدء تشغيل مروم FM AI v3.0")
    print("=" * 50)
    print(f"🌐 الواجهة: https://kruri.qzz.io")
    print(f"🔌 توثيق API: https://kruri.qzz.io/api/docs")
    print(f"📱 API Endpoint: https://kruri.qzz.io/api/v1/chat")
    print(f"💾 تخزين المحادثات: localStorage (في متصفح المستخدم)")
    print("=" * 50)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)