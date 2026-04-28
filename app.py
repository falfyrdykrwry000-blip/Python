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
CORS(app)

# إعدادات API
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# قائمة نماذج الذكاء الاصطناعي
AVAILABLE_MODELS = {
    "llama-3.3-70b-versatile": "🦙 مروم FM سريع",
    "llama3-70b-8192": "🚀 مروم FM فائق",
    "mixtral-8x7b-32768": "🧠 مروم FM متقدم",
    "gemma2-9b-it": "⚡ مروم FM متوازن"
}

# ============================================
# دالة الاتصال بـ Groq API (مصححة)
# ============================================
def chat_with_groq(messages, model="llama3-8b-8192"):
    """الاتصال بـ Groq API مع معالجة الأخطاء"""
    
    if not GROQ_API_KEY:
        return "⚠️ عذراً، مفتاح API غير مضبوط. يرجى إضافة GROQ_API_KEY في المتغيرات البيئية."
    
    # التحقق من صحة المفتاح (يجب أن يبدأ بـ gsk_)
    if not GROQ_API_KEY.startswith('gsk_'):
        return "⚠️ مفتاح API غير صالح. يجب أن يبدأ بـ gsk_"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # التأكد من صيغة الرسائل
    if not messages or not isinstance(messages, list):
        messages = [{"role": "user", "content": "مرحباً"}]
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 0.9,
        "stream": False
    }
    
    try:
        print(f"📤 إرسال طلب إلى Groq API مع نموذج: {model}")
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=60)
        
        print(f"📥 استجابة API: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            reply = result['choices'][0]['message']['content']
            return reply
        else:
            error_detail = response.json() if response.text else {}
            error_msg = error_detail.get('error', {}).get('message', str(response.status_code))
            print(f"❌ خطأ API: {error_msg}")
            return f"⚠️ خطأ تقني: {error_msg}"
            
    except requests.exceptions.Timeout:
        return "⚠️ انتهت مهلة الاتصال. يرجى المحاولة مرة أخرى."
    except requests.exceptions.ConnectionError:
        return "⚠️ فشل الاتصال بالإنترنت. تحقق من اتصالك."
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {str(e)}")
        return f"⚠️ خطأ تقني: {str(e)}"

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
# قالب HTML الرئيسي
# ============================================

MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مروم FM - منصة الذكاء الاصطناعي</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        :root{
            --bg:#0a0a2a;--card:#1a1a3a;--text:#fff;--text-sec:#aaa;
            --primary:#ff6b00;--secondary:#ff2b7a;--input:#0f0f2a;
        }
        [data-theme="light"]{
            --bg:#f0f2f5;--card:#ffffff;--text:#1a1a2e;--text-sec:#666;
            --primary:#ff6b00;--secondary:#ff2b7a;--input:#e8e8ec;
        }
        body{
            font-family:'Cairo','Segoe UI',sans-serif;
            background:radial-gradient(ellipse at top,var(--bg),#050510);
            color:var(--text);
            min-height:100vh;
        }
        .navbar{
            background:var(--card);
            padding:1rem 2rem;
            display:flex;
            justify-content:space-between;
            align-items:center;
            border-bottom:2px solid var(--primary);
            position:sticky;
            top:0;
            z-index:100;
        }
        .logo{
            font-size:1.5rem;
            font-weight:800;
            background:linear-gradient(135deg,var(--primary),var(--secondary));
            -webkit-background-clip:text;
            background-clip:text;
            color:transparent;
        }
        .menu-btn{
            background:none;
            border:none;
            font-size:1.8rem;
            cursor:pointer;
            color:var(--text);
        }
        .sidebar{
            position:fixed;
            top:0;
            right:-280px;
            width:280px;
            height:100%;
            background:var(--card);
            z-index:1000;
            transition:0.3s;
            padding:2rem 1rem;
            overflow-y:auto;
        }
        .sidebar.open{right:0}
        .sidebar-header{display:flex;justify-content:space-between;margin-bottom:2rem}
        .close-menu{background:none;border:none;font-size:1.5rem;cursor:pointer;color:var(--text)}
        .sidebar-section{margin-bottom:1.5rem}
        .sidebar-section h3{color:var(--primary);margin-bottom:0.8rem;font-size:1rem}
        .sidebar-item{
            display:flex;
            align-items:center;
            gap:0.8rem;
            padding:0.7rem;
            border-radius:12px;
            cursor:pointer;
            transition:0.3s;
        }
        .sidebar-item:hover{background:rgba(255,107,0,0.2)}
        .theme-toggle{
            display:flex;
            justify-content:space-between;
            align-items:center;
            padding:0.7rem;
            background:var(--input);
            border-radius:40px;
            cursor:pointer;
        }
        .overlay{
            position:fixed;
            top:0;
            left:0;
            width:100%;
            height:100%;
            background:rgba(0,0,0,0.5);
            z-index:999;
            display:none;
        }
        .overlay.active{display:block}
        .container{max-width:1200px;margin:0 auto;padding:2rem}
        .card{
            background:var(--card);
            border-radius:28px;
            padding:1.5rem;
            margin-bottom:1.5rem;
            border:1px solid rgba(255,107,0,0.3);
        }
        .card h2{
            background:linear-gradient(90deg,var(--primary),var(--secondary));
            -webkit-background-clip:text;
            background-clip:text;
            color:transparent;
            margin-bottom:1rem;
        }
        .chat-container{display:flex;flex-direction:column;height:500px}
        .chat-messages{
            flex:1;
            overflow-y:auto;
            padding:1rem;
            background:var(--input);
            border-radius:20px;
            margin-bottom:1rem;
        }
        .message{
            margin-bottom:1rem;
            padding:1rem;
            border-radius:20px;
            max-width:85%;
            animation:fadeIn 0.3s;
        }
        @keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        .message.user{
            background:linear-gradient(135deg,var(--primary)22,var(--secondary)22);
            border-right:3px solid var(--primary);
            margin-right:auto;
            text-align:right;
        }
        .message.assistant{
            background:rgba(255,255,255,0.05);
            border-left:3px solid var(--secondary);
            margin-left:auto;
            text-align:left;
        }
        .chat-input{display:flex;gap:0.8rem}
        .chat-input textarea{
            flex:1;
            padding:1rem;
            border:1px solid rgba(255,107,0,0.3);
            border-radius:20px;
            background:var(--input);
            color:var(--text);
            resize:none;
            font-family:inherit;
        }
        .chat-input button{
            background:linear-gradient(135deg,var(--primary),var(--secondary));
            border:none;
            border-radius:20px;
            padding:0 2rem;
            cursor:pointer;
            font-weight:bold;
        }
        .tools-grid{
            display:grid;
            grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
            gap:1rem;
            margin:1rem 0;
        }
        .tool-btn{
            background:rgba(255,107,0,0.15);
            border:1px solid rgba(255,107,0,0.3);
            padding:0.8rem;
            border-radius:16px;
            cursor:pointer;
            text-align:center;
            transition:0.3s;
        }
        .tool-btn:hover{background:rgba(255,107,0,0.3);transform:translateY(-2px)}
        select,textarea{
            width:100%;
            padding:0.8rem;
            margin:0.5rem 0;
            border:1px solid rgba(255,107,0,0.3);
            border-radius:16px;
            background:var(--input);
            color:var(--text);
        }
        button{
            background:linear-gradient(135deg,var(--primary),var(--secondary));
            border:none;
            padding:0.8rem 1.5rem;
            border-radius:40px;
            cursor:pointer;
            font-weight:bold;
        }
        .result-box{
            background:var(--input);
            padding:1rem;
            border-radius:20px;
            margin-top:1rem;
            white-space:pre-wrap;
        }
        .api-doc{
            background:var(--input);
            padding:1rem;
            border-radius:16px;
            font-family:monospace;
            font-size:0.8rem;
            margin:1rem 0;
            overflow-x:auto;
        }
        .footer{text-align:center;padding:1.5rem;color:var(--text-sec);font-size:0.8rem}
        @media (max-width:768px){.container{padding:1rem}.message{max-width:95%}}
        ::-webkit-scrollbar{width:6px}
        ::-webkit-scrollbar-track{background:var(--input)}
        ::-webkit-scrollbar-thumb{background:var(--primary);border-radius:10px}
    </style>
</head>
<body>
    <div class="overlay" id="overlay"></div>
    <nav class="navbar">
        <button class="menu-btn" id="menuBtn">☰</button>
        <div class="logo">🎙️ مروم FM</div>
        <div style="width:40px"></div>
    </nav>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header"><h3>⚙️ الإعدادات</h3><button class="close-menu" id="closeMenu">✕</button></div>
        <div class="sidebar-section"><h3>🎨 المظهر</h3><div class="theme-toggle" id="themeToggle"><span>🌙 ليلي</span><span>☀️ نهاري</span></div></div>
        <div class="sidebar-section"><h3>🧠 النموذج</h3><select id="globalModel"><option value="llama3-8b-8192">🦙 سريع</option><option value="mixtral-8x7b-32768">🧠 متقدم</option><option value="gemma2-9b-it">⚡ متوازن</option></select></div>
        <div class="sidebar-section"><h3>🎛️ إعدادات</h3><div class="sidebar-item" onclick="clearChat()">🗑️ مسح المحادثة</div><div class="sidebar-item" onclick="window.location.reload()">🔄 تحديث</div></div>
        <div class="sidebar-section"><h3>🔗 الروابط</h3><div class="sidebar-item" onclick="showTab('chat')">💬 المحادثة</div><div class="sidebar-item" onclick="showTab('tools')">🛠️ الأدوات</div><div class="sidebar-item" onclick="showTab('docs')">📖 توثيق API</div></div>
    </div>
    <div class="container">
        <div id="chatTab">
            <div class="card">
                <h2>💬 محادثة ذكية</h2>
                <div class="chat-container">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message assistant"><strong>🎙️ مروم FM</strong><p>مرحباً بك! كيف يمكنني مساعدتك اليوم؟</p><div class="message-time">الآن</div></div>
                    </div>
                    <div class="chat-input">
                        <textarea id="messageInput" rows="2" placeholder="اكتب رسالتك هنا..."></textarea>
                        <button onclick="sendMessage()">إرسال ➤</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="toolsTab" style="display:none">
            <div class="card">
                <h2>🛠️ أدوات ذكية</h2>
                <div class="tools-grid">
                    <div class="tool-btn" onclick="analyze('summary')">📝 تلخيص</div>
                    <div class="tool-btn" onclick="analyze('translate')">🌐 ترجمة</div>
                    <div class="tool-btn" onclick="analyze('grammar')">✍️ تدقيق</div>
                    <div class="tool-btn" onclick="analyze('sentiment')">😊 تحليل</div>
                    <div class="tool-btn" onclick="analyze('ideas')">💡 أفكار</div>
                </div>
                <textarea id="toolInput" rows="5" placeholder="أدخل النص هنا..."></textarea>
                <button onclick="runTool()">تنفيذ</button>
                <div id="toolResult" class="result-box"></div>
            </div>
        </div>
        <div id="docsTab" style="display:none">
            <div class="card">
                <h2>📖 توثيق API</h2>
                <div class="api-doc"><strong>GET</strong> /api/health<br><strong>GET</strong> /api/models<br><strong>POST</strong> /api/chat (X-API-Key)<br><strong>POST</strong> /api/tool (X-API-Key)</div>
            </div>
        </div>
    </div>
    <div class="footer"><p>© 2026 مروم FM - جميع الحقوق محفوظة</p></div>
    <script>
        let currentAction='summary';let currentModel='llama3-8b-8192';
        const menuBtn=document.getElementById('menuBtn'),sidebar=document.getElementById('sidebar'),closeMenu=document.getElementById('closeMenu'),overlay=document.getElementById('overlay');
        function openSidebar(){sidebar.classList.add('open');overlay.classList.add('active');}
        function closeSidebar(){sidebar.classList.remove('open');overlay.classList.remove('active');}
        menuBtn.onclick=openSidebar;closeMenu.onclick=closeSidebar;overlay.onclick=closeSidebar;
        const themeToggle=document.getElementById('themeToggle');
        if(localStorage.getItem('theme')==='light')document.documentElement.setAttribute('data-theme','light');
        themeToggle.onclick=()=>{let t=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',t);localStorage.setItem('theme',t);};
        function showTab(tab){document.getElementById('chatTab').style.display='none';document.getElementById('toolsTab').style.display='none';document.getElementById('docsTab').style.display='none';if(tab==='chat')document.getElementById('chatTab').style.display='block';if(tab==='tools')document.getElementById('toolsTab').style.display='block';if(tab==='docs')document.getElementById('docsTab').style.display='block';closeSidebar();}
        document.getElementById('globalModel').onchange=function(){currentModel=this.value;};
        async function sendMessage(){
            const input=document.getElementById('messageInput'),message=input.value.trim();
            if(!message)return;
            const msgs=document.getElementById('chatMessages');
            msgs.innerHTML+=`<div class="message user"><strong>👤 أنت</strong><p>${escapeHtml(message)}</p><div class="message-time">الآن</div></div>`;
            input.value='';msgs.scrollTop=msgs.scrollHeight;
            msgs.innerHTML+=`<div class="message assistant" id="loadingMsg"><strong>🎙️ مروم FM</strong><p>🤔 جاري التفكير...</p></div>`;
            msgs.scrollTop=msgs.scrollHeight;
            try{
                const res=await fetch('/chat/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:message,model:currentModel})});
                const data=await res.json();
                document.getElementById('loadingMsg')?.remove();
                msgs.innerHTML+=`<div class="message assistant"><strong>🎙️ مروم FM</strong><p>${escapeHtml(data.reply)}</p><div class="message-time">الآن</div></div>`;
                msgs.scrollTop=msgs.scrollHeight;
            }catch(e){
                document.getElementById('loadingMsg')?.remove();
                msgs.innerHTML+=`<div class="message assistant"><strong>🎙️ مروم FM</strong><p>❌ خطأ تقني</p></div>`;
            }
        }
        function clearChat(){document.getElementById('chatMessages').innerHTML='<div class="message assistant"><strong>🎙️ مروم FM</strong><p>مرحباً بك! كيف يمكنني مساعدتك اليوم؟</p><div class="message-time">الآن</div></div>';closeSidebar();}
        function analyze(action){currentAction=action;const actions={summary:'قم بتلخيص النص:',translate:'ترجم النص:',grammar:'صحح الأخطاء:',sentiment:'حلل المشاعر:',ideas:'اقترح 5 أفكار:'};document.getElementById('toolInput').placeholder=actions[action];document.querySelectorAll('.tool-btn').forEach(btn=>btn.style.background='rgba(255,107,0,0.15)');event.target.style.background='rgba(255,107,0,0.4)';}
        async function runTool(){
            const text=document.getElementById('toolInput').value;
            if(!text){alert('أدخل نصاً');return;}
            document.getElementById('toolResult').innerHTML='<p>🤔 جاري المعالجة...</p>';
            try{
                const res=await fetch('/tool/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:currentAction,text:text})});
                const data=await res.json();
                document.getElementById('toolResult').innerHTML=`<p><strong>النتيجة:</strong></p><p>${data.result.replace(/\\n/g,'<br>')}</p>`;
            }catch(e){document.getElementById('toolResult').innerHTML='<p>❌ خطأ</p>';}
        }
        function escapeHtml(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
        document.getElementById('messageInput').addEventListener('keypress',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}});
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
    
    if not user_message:
        return jsonify({"reply": "الرجاء كتابة رسالة"}), 200
    
    messages = [{"role": "user", "content": user_message}]
    reply = chat_with_groq(messages, model)
    
    return jsonify({"reply": reply})

@app.route('/tool/run', methods=['POST'])
def tool_run():
    data = request.get_json()
    action = data.get('action')
    text = data.get('text')
    
    prompts = {
        'summary': f"لخص النص التالي بشكل موجز:\n\n{text}",
        'translate': f"ترجم النص التالي إلى العربية:\n\n{text}",
        'grammar': f"صحح الأخطاء في النص التالي:\n\n{text}",
        'sentiment': f"حلل المشاعر في النص التالي:\n\n{text}",
        'ideas': f"اقترح 5 أفكار من النص التالي:\n\n{text}"
    }
    
    messages = [{"role": "user", "content": prompts.get(action, prompts['summary'])}]
    result = chat_with_groq(messages)
    
    return jsonify({"result": result})

# ============================================
# API للتطبيقات الخارجية
# ============================================

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        "status": "healthy",
        "api_key_configured": bool(GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_')),
        "time": datetime.now().isoformat()
    })

@app.route('/api/models', methods=['GET'])
def api_models():
    return jsonify(AVAILABLE_MODELS)

@app.route('/api/chat', methods=['POST'])
@api_key_required
def api_chat():
    data = request.get_json()
    user_message = data.get('message', '')
    model = data.get('model', 'llama3-8b-8192')
    
    if not user_message:
        return jsonify({"error": "الرسالة مطلوبة"}), 400
    
    messages = [{"role": "user", "content": user_message}]
    reply = chat_with_groq(messages, model)
    
    return jsonify({"success": True, "reply": reply})

@app.route('/api/tool', methods=['POST'])
@api_key_required
def api_tool():
    data = request.get_json()
    action = data.get('action', 'summary')
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "النص مطلوب"}), 400
    
    prompts = {
        'summary': f"لخص النص التالي:\n\n{text}",
        'translate': f"ترجم النص التالي إلى العربية:\n\n{text}",
        'grammar': f"صحح الأخطاء في النص التالي:\n\n{text}",
        'sentiment': f"حلل المشاعر في النص التالي:\n\n{text}",
        'ideas': f"اقترح 5 أفكار من النص التالي:\n\n{text}"
    }
    
    messages = [{"role": "user", "content": prompts.get(action, prompts['summary'])}]
    result = chat_with_groq(messages)
    
    return jsonify({"success": True, "result": result})

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    print("🎙️ بدء تشغيل منصة مروم FM...")
    print(f"🔑 مفتاح API: {'موجود ✅' if GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_') else 'غير موجود ❌'}")
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
