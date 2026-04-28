"""
منصة مروم FM - الذكاء الاصطناعي المتكامل
نسخة API مفتوحة - بدون قاعدة بيانات - بدون تسجيل دخول
جميع الحقوق محفوظة © مروم FM
"""

from flask import Flask, render_template_string, request, jsonify, session
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
CORS(app)  # السماح لجميع التطبيقات بالاتصال

# إعدادات API
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# قائمة نماذج الذكاء الاصطناعي
AVAILABLE_MODELS = {
    "llama3-8b-8192": "🦙 مروم FM سريع",
    "mixtral-8x7b-32768": "🧠 مروم FM متقدم",
    "gemma2-9b-it": "⚡ مروم FM متوازن"
}

# ============================================
# دوال مساعدة
# ============================================
def chat_with_groq(messages, model="llama3-8b-8192"):
    """الاتصال بـ Groq API"""
    if not GROQ_API_KEY:
        return "⚠️ عذراً، مفتاح API غير مضبوط. يرجى إضافة GROQ_API_KEY في المتغيرات البيئية."
    
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

# Decorator لمفتاح API (للتطبيقات الخارجية)
def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != GROQ_API_KEY:
            return jsonify({"error": "مفتاح API غير صحيح"}), 401
        return f(*args, **kwargs)
    return decorated

# ============================================
# قالب HTML الرئيسي (مع قائمة همبركر ووضع ليلي)
# ============================================

MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl" data-theme="dark">
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
        
        /* ========== الثيمات (Dark/Light) ========== */
        :root {
            --bg-primary: #0a0a2a;
            --bg-secondary: #050510;
            --card-bg: rgba(20, 20, 50, 0.8);
            --text-primary: #ffffff;
            --text-secondary: #cccccc;
            --border-color: rgba(255, 107, 0, 0.3);
            --gradient-start: #ff6b00;
            --gradient-end: #ff2b7a;
            --shadow: rgba(0, 0, 0, 0.3);
            --input-bg: rgba(0, 0, 0, 0.5);
            --message-user: linear-gradient(135deg, #ff6b0022, #ff2b7a22);
            --message-ai: rgba(255, 255, 255, 0.05);
        }
        
        [data-theme="light"] {
            --bg-primary: #f0f2f5;
            --bg-secondary: #e4e6e9;
            --card-bg: rgba(255, 255, 255, 0.9);
            --text-primary: #1a1a2e;
            --text-secondary: #4a4a6a;
            --border-color: rgba(255, 107, 0, 0.3);
            --shadow: rgba(0, 0, 0, 0.1);
            --input-bg: rgba(0, 0, 0, 0.05);
            --message-user: linear-gradient(135deg, #ff6b0011, #ff2b7a11);
            --message-ai: rgba(0, 0, 0, 0.03);
        }
        
        body {
            font-family: 'Cairo', 'Tajawal', 'Segoe UI', sans-serif;
            background: radial-gradient(ellipse at top, var(--bg-primary), var(--bg-secondary));
            min-height: 100vh;
            color: var(--text-primary);
            transition: all 0.3s ease;
        }
        
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800&display=swap');
        
        /* ========== شريط التنقل ========== */
        .navbar {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            padding: 0.8rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        
        .logo {
            font-size: 1.6rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        
        .menu-btn {
            background: none;
            border: none;
            font-size: 1.8rem;
            cursor: pointer;
            color: var(--text-primary);
            padding: 0.5rem;
        }
        
        /* ========== القائمة الجانبية (همبركر) ========== */
        .sidebar {
            position: fixed;
            top: 0;
            right: -300px;
            width: 280px;
            height: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border-left: 1px solid var(--border-color);
            z-index: 1100;
            transition: right 0.3s ease;
            padding: 2rem 1rem;
            overflow-y: auto;
        }
        
        .sidebar.open {
            right: 0;
        }
        
        .sidebar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .close-menu {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-primary);
        }
        
        .sidebar-section {
            margin-bottom: 2rem;
        }
        
        .sidebar-section h3 {
            font-size: 1rem;
            color: var(--gradient-start);
            margin-bottom: 1rem;
        }
        
        .sidebar-item {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            padding: 0.8rem;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 0.5rem;
        }
        
        .sidebar-item:hover {
            background: rgba(255, 107, 0, 0.2);
        }
        
        .theme-toggle {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.8rem;
            background: var(--input-bg);
            border-radius: 40px;
            cursor: pointer;
        }
        
        /* ========== الحاوية ========== */
        .container {
            max-width: 1300px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(15px);
            border-radius: 28px;
            padding: 1.8rem;
            margin-bottom: 1.8rem;
            border: 1px solid var(--border-color);
            transition: all 0.3s;
        }
        
        .card h2 {
            background: linear-gradient(90deg, var(--gradient-start), var(--gradient-end));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 1.2rem;
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
            background: var(--input-bg);
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
            background: var(--message-user);
            border-right: 3px solid var(--gradient-start);
            margin-right: auto;
            text-align: right;
        }
        
        .message.assistant {
            background: var(--message-ai);
            border-left: 3px solid var(--gradient-end);
            margin-left: auto;
            text-align: left;
        }
        
        .message-time {
            font-size: 0.7rem;
            color: var(--text-secondary);
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
            border: 1px solid var(--border-color);
            border-radius: 20px;
            background: var(--input-bg);
            color: var(--text-primary);
            resize: none;
            font-family: inherit;
            font-size: 1rem;
        }
        
        .chat-input textarea:focus {
            outline: none;
            border-color: var(--gradient-start);
        }
        
        .chat-input button {
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            border: none;
            border-radius: 20px;
            padding: 0 2rem;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
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
            border: 1px solid var(--border-color);
            padding: 1rem;
            border-radius: 16px;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s;
        }
        
        .tool-btn:hover {
            background: rgba(255, 107, 0, 0.3);
            transform: translateY(-3px);
        }
        
        select, textarea {
            width: 100%;
            padding: 0.8rem;
            margin: 0.5rem 0;
            border: 1px solid var(--border-color);
            border-radius: 16px;
            background: var(--input-bg);
            color: var(--text-primary);
            font-size: 1rem;
        }
        
        button {
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            border: none;
            padding: 0.8rem 1.8rem;
            border-radius: 40px;
            cursor: pointer;
            font-weight: bold;
            color: white;
        }
        
        .result-box {
            background: var(--input-bg);
            padding: 1.2rem;
            border-radius: 20px;
            margin-top: 1rem;
            white-space: pre-wrap;
            border: 1px solid var(--border-color);
        }
        
        /* التوثيق */
        .api-doc {
            background: var(--input-bg);
            border-radius: 16px;
            padding: 1rem;
            margin: 1rem 0;
            font-family: monospace;
            font-size: 0.8rem;
            overflow-x: auto;
        }
        
        /* طبقة الإخفاء */
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1050;
            display: none;
        }
        
        .overlay.active {
            display: block;
        }
        
        /* التذييل */
        .footer {
            text-align: center;
            padding: 1.5rem;
            background: var(--card-bg);
            margin-top: 2rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .message { max-width: 95%; }
        }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-secondary); border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: var(--gradient-start); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="overlay" id="overlay"></div>
    
    <nav class="navbar">
        <button class="menu-btn" id="menuBtn">☰</button>
        <div class="logo">🎙️ مروم FM <span style="font-size:0.7rem;">AI</span></div>
        <div style="width: 40px;"></div>
    </nav>
    
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h3>⚙️ الإعدادات</h3>
            <button class="close-menu" id="closeMenu">✕</button>
        </div>
        
        <div class="sidebar-section">
            <h3>🎨 المظهر</h3>
            <div class="theme-toggle" id="themeToggle">
                <span>🌙 وضع ليلي</span>
                <span>☀️ وضع نهاري</span>
            </div>
        </div>
        
        <div class="sidebar-section">
            <h3>🧠 نموذج الذكاء</h3>
            <select id="globalModel">
                <option value="llama3-8b-8192">🦙 مروم FM سريع</option>
                <option value="mixtral-8x7b-32768">🧠 مروم FM متقدم</option>
                <option value="gemma2-9b-it">⚡ مروم FM متوازن</option>
            </select>
        </div>
        
        <div class="sidebar-section">
            <h3>🎛️ إعدادات المحادثة</h3>
            <div class="sidebar-item" onclick="clearChat()">
                <span>🗑️</span> <span>مسح المحادثة</span>
            </div>
            <div class="sidebar-item" onclick="window.location.reload()">
                <span>🔄</span> <span>تحديث الصفحة</span>
            </div>
        </div>
        
        <div class="sidebar-section">
            <h3>🔗 الروابط</h3>
            <div class="sidebar-item" onclick="showTab('chat')">
                <span>💬</span> <span>المحادثة</span>
            </div>
            <div class="sidebar-item" onclick="showTab('tools')">
                <span>🛠️</span> <span>أدوات الذكاء</span>
            </div>
            <div class="sidebar-item" onclick="showTab('docs')">
                <span>📖</span> <span>توثيق API</span>
            </div>
        </div>
        
        <div class="sidebar-section">
            <h3>ℹ️ معلومات</h3>
            <div class="sidebar-item">
                <span>📅</span> <span>مروم FM v3.0</span>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div id="chatTab" class="tab-content">
            <div class="card">
                <h2>💬 محادثة ذكية</h2>
                <div class="chat-container">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message assistant">
                            <strong>🎙️ مروم FM</strong>
                            <p>مرحباً بك في منصة مروم FM! كيف يمكنني مساعدتك اليوم؟</p>
                            <div class="message-time">الآن</div>
                        </div>
                    </div>
                    <div class="chat-input">
                        <textarea id="messageInput" rows="2" placeholder="اكتب رسالتك هنا..."></textarea>
                        <button onclick="sendMessage()">إرسال ➤</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="toolsTab" class="tab-content" style="display:none;">
            <div class="card">
                <h2>🛠️ أدوات مروم FM الذكية</h2>
                <div class="tools-grid">
                    <div class="tool-btn" onclick="analyze('summary')">📝 تلخيص ذكي</div>
                    <div class="tool-btn" onclick="analyze('translate')">🌐 ترجمة فورية</div>
                    <div class="tool-btn" onclick="analyze('grammar')">✍️ تدقيق لغوي</div>
                    <div class="tool-btn" onclick="analyze('sentiment')">😊 تحليل المشاعر</div>
                    <div class="tool-btn" onclick="analyze('code')">💻 شرح أكواد</div>
                    <div class="tool-btn" onclick="analyze('ideas')">💡 توليد أفكار</div>
                </div>
                <textarea id="toolInput" rows="5" placeholder="أدخل النص هنا..."></textarea>
                <button onclick="runTool()">تنفيذ ➤</button>
                <div id="toolResult" class="result-box"></div>
            </div>
        </div>
        
        <div id="docsTab" class="tab-content" style="display:none;">
            <div class="card">
                <h2>📖 توثيق API - مروم FM</h2>
                <p>يمكنك ربط تطبيق APK الخاص بك مع مروم FM باستخدام هذه الواجهات:</p>
                
                <h3>🔑 المصادقة</h3>
                <div class="api-doc">
                    headers: { "X-API-Key": "YOUR_GROQ_API_KEY" }
                </div>
                
                <h3>📡 نقطة النهاية: المحادثة</h3>
                <div class="api-doc">
                    <strong>POST</strong> /api/chat<br>
                    {
                        "message": "مرحباً",
                        "model": "llama3-8b-8192"
                    }
                </div>
                
                <h3>📡 نقطة النهاية: الأدوات</h3>
                <div class="api-doc">
                    <strong>POST</strong> /api/tool<br>
                    {
                        "action": "summary",
                        "text": "النص المراد معالجته"
                    }
                </div>
                
                <h3>📡 نقطة النهاية: النماذج</h3>
                <div class="api-doc">
                    <strong>GET</strong> /api/models<br>
                    يعرض قائمة النماذج المتاحة
                </div>
                
                <h3>📡 نقطة النهاية: الصحة</h3>
                <div class="api-doc">
                    <strong>GET</strong> /api/health<br>
                    يتحقق من حالة الخادم والمفتاح
                </div>
                
                <h3>🐍 مثال باستخدام Python</h3>
                <div class="api-doc">
                    import requests<br><br>
                    url = "https://kruri.qzz.io/api/chat"<br>
                    headers = {"X-API-Key": "your-key"}<br>
                    data = {"message": "مرحباً", "model": "llama3-8b-8192"}<br>
                    response = requests.post(url, json=data, headers=headers)<br>
                    print(response.json())
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>© 2026 مروم FM - جميع الحقوق محفوظة | ذكاء اصطناعي متقدم</p>
    </div>
    
    <script>
        let currentAction = 'summary';
        let currentModel = 'llama3-8b-8192';
        
        // ========== القائمة الجانبية ==========
        const menuBtn = document.getElementById('menuBtn');
        const sidebar = document.getElementById('sidebar');
        const closeMenu = document.getElementById('closeMenu');
        const overlay = document.getElementById('overlay');
        
        function openSidebar() {
            sidebar.classList.add('open');
            overlay.classList.add('active');
        }
        
        function closeSidebar() {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }
        
        menuBtn.onclick = openSidebar;
        closeMenu.onclick = closeSidebar;
        overlay.onclick = closeSidebar;
        
        // ========== الوضع الليلي والنهاري ==========
        const themeToggle = document.getElementById('themeToggle');
        const htmlElement = document.documentElement;
        
        if (localStorage.getItem('theme') === 'light') {
            htmlElement.setAttribute('data-theme', 'light');
        }
        
        themeToggle.onclick = () => {
            if (htmlElement.getAttribute('data-theme') === 'dark') {
                htmlElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            } else {
                htmlElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            }
        };
        
        // ========== التبديل بين التبويبات ==========
        function showTab(tab) {
            document.getElementById('chatTab').style.display = 'none';
            document.getElementById('toolsTab').style.display = 'none';
            document.getElementById('docsTab').style.display = 'none';
            
            if (tab === 'chat') document.getElementById('chatTab').style.display = 'block';
            if (tab === 'tools') document.getElementById('toolsTab').style.display = 'block';
            if (tab === 'docs') document.getElementById('docsTab').style.display = 'block';
            
            closeSidebar();
        }
        
        // ========== تحديث النموذج من الإعدادات ==========
        document.getElementById('globalModel').onchange = function() {
            currentModel = this.value;
        };
        
        // ========== المحادثة ==========
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;
            
            const messagesDiv = document.getElementById('chatMessages');
            
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.innerHTML = '<strong>👤 أنت</strong><p>' + escapeHtml(message) + '</p><div class="message-time">الآن</div>';
            messagesDiv.appendChild(userMsg);
            
            input.value = '';
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'message assistant';
            loadingMsg.id = 'loadingMsg';
            loadingMsg.innerHTML = '<strong>🎙️ مروم FM</strong><p>🤔 جاري التفكير...</p>';
            messagesDiv.appendChild(loadingMsg);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            try {
                const response = await fetch('/chat/send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message, model: currentModel})
                });
                const data = await response.json();
                
                document.getElementById('loadingMsg').remove();
                const aiMsg = document.createElement('div');
                aiMsg.className = 'message assistant';
                aiMsg.innerHTML = '<strong>🎙️ مروم FM</strong><p>' + escapeHtml(data.reply) + '</p><div class="message-time">الآن</div>';
                messagesDiv.appendChild(aiMsg);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            } catch(error) {
                document.getElementById('loadingMsg').remove();
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message assistant';
                errorMsg.innerHTML = '<strong>🎙️ مروم FM</strong><p>❌ عذراً، حدث خطأ تقني</p>';
                messagesDiv.appendChild(errorMsg);
            }
        }
        
        function clearChat() {
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.innerHTML = '<div class="message assistant"><strong>🎙️ مروم FM</strong><p>مرحباً بك في منصة مروم FM! كيف يمكنني مساعدتك اليوم؟</p><div class="message-time">الآن</div></div>';
            closeSidebar();
        }
        
        // ========== الأدوات ==========
        function analyze(action) {
            currentAction = action;
            const actions = {
                'summary': 'قم بتلخيص النص التالي بشكل احترافي:',
                'translate': 'ترجم النص التالي إلى العربية:',
                'grammar': 'صحح الأخطاء في النص التالي:',
                'sentiment': 'حلل المشاعر في النص التالي:',
                'code': 'اشرح الكود التالي:',
                'ideas': 'اقترح 5 أفكار من النص التالي:'
            };
            document.getElementById('toolInput').placeholder = actions[action];
            document.querySelectorAll('.tool-btn').forEach(btn => btn.style.background = 'rgba(255,107,0,0.15)');
            event.target.style.background = 'rgba(255,107,0,0.4)';
        }
        
        async function runTool() {
            const text = document.getElementById('toolInput').value;
            if (!text) {
                alert('الرجاء إدخال نص');
                return;
            }
            
            document.getElementById('toolResult').innerHTML = '<p>🤔 جاري المعالجة...</p>';
            
            try {
                const response = await fetch('/tool/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: currentAction, text: text})
                });
                const data = await response.json();
                document.getElementById('toolResult').innerHTML = '<p><strong>النتيجة:</strong></p><p>' + data.result.replace(/\\n/g, '<br>') + '</p>';
            } catch(error) {
                document.getElementById('toolResult').innerHTML = '<p>❌ خطأ تقني</p>';
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
        
        analyze('summary');
    </script>
</body>
</html>
'''

# ============================================
# المسارات
# ============================================

@app.route('/')
def index():
    return render_template_string(MAIN_TEMPLATE)

@app.route('/chat/send', methods=['POST'])
def chat_send():
    data = request.get_json()
    user_message = data.get('message', '')
    model = data.get('model', 'llama3-8b-8192')
    
    messages = [
        {"role": "user", "content": user_message}
    ]
    
    reply = chat_with_groq(messages, model)
    return jsonify({"reply": reply})

@app.route('/tool/run', methods=['POST'])
def tool_run():
    data = request.get_json()
    action = data.get('action')
    text = data.get('text')
    
    prompts = {
        'summary': f"قم بتلخيص النص التالي بشكل احترافي وموجز:\n\n{text}",
        'translate': f"ترجم النص التالي إلى اللغة العربية الفصحى:\n\n{text}",
        'grammar': f"صحح الأخطاء الإملائية والنحوية في النص التالي:\n\n{text}",
        'sentiment': f"حلل المشاعر في النص التالي (إيجابي/سلبي/محايد):\n\n{text}",
        'code': f"اشرح الكود التالي بطريقة بسيطة:\n\n{text}",
        'ideas': f"اقترح 5 أفكار إبداعية من النص التالي:\n\n{text}"
    }
    
    messages = [{"role": "user", "content": prompts.get(action, prompts['summary'])}]
    result = chat_with_groq(messages)
    
    return jsonify({"result": result})

# ============================================
# API للتطبيقات الخارجية (لربط APK)
# ============================================

@app.route('/api/health', methods=['GET'])
def api_health():
    """التحقق من صحة الخادم"""
    return jsonify({
        "status": "healthy",
        "api_key_configured": bool(GROQ_API_KEY),
        "time": datetime.now().isoformat(),
        "version": "3.0.0"
    })

@app.route('/api/models', methods=['GET'])
def api_models():
    """قائمة النماذج المتاحة"""
    return jsonify(AVAILABLE_MODELS)

@app.route('/api/chat', methods=['POST'])
@api_key_required
def api_chat():
    """واجهة المحادثة للتطبيقات الخارجية"""
    data = request.get_json()
    user_message = data.get('message', '')
    model = data.get('model', 'llama3-8b-8192')
    
    if not user_message:
        return jsonify({"error": "الرسالة مطلوبة"}), 400
    
    if model not in AVAILABLE_MODELS:
        model = "llama3-8b-8192"
    
    messages = [{"role": "user", "content": user_message}]
    reply = chat_with_groq(messages, model)
    
    return jsonify({
        "success": True,
        "reply": reply,
        "model": model,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/tool', methods=['POST'])
@api_key_required
def api_tool():
    """واجهة الأدوات للتطبيقات الخارجية"""
    data = request.get_json()
    action = data.get('action', 'summary')
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "النص مطلوب"}), 400
    
    prompts = {
        'summary': f"قم بتلخيص النص التالي:\n\n{text}",
        'translate': f"ترجم النص التالي إلى العربية:\n\n{text}",
        'grammar': f"صحح الأخطاء في النص التالي:\n\n{text}",
        'sentiment': f"حلل المشاعر في النص التالي:\n\n{text}",
        'code': f"اشرح الكود التالي:\n\n{text}",
        'ideas': f"اقترح 5 أفكار من النص التالي:\n\n{text}"
    }
    
    messages = [{"role": "user", "content": prompts.get(action, prompts['summary'])}]
    result = chat_with_groq(messages)
    
    return jsonify({
        "success": True,
        "result": result,
        "action": action,
        "timestamp": datetime.now().isoformat()
    })

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    print("🎙️ بدء تشغيل منصة مروم FM للذكاء الاصطناعي...")
    print(f"🔑 مفتاح API: {'موجود ✅' if GROQ_API_KEY else 'غير موجود ❌'}")
    print("📖 توثيق API متاح على: /api/health, /api/chat, /api/tool, /api/models")
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
