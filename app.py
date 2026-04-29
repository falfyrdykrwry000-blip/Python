"""
منصة مروم FM - Gemini AI
جميع الحقوق محفوظة © مروم FM
"""

from flask import Flask, render_template_string, request, jsonify, Response
from flask_cors import CORS
import os
import requests
from datetime import datetime
from urllib.parse import quote
from google import genai

# ============================================
# تهيئة التطبيق
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'maroom-secret-key-2026')
CORS(app)

# إعدادات Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

AVAILABLE_MODELS = {
    "gemini-2.0-flash": "🚀 Gemini 2.0 Flash",
    "gemini-2.0-flash-lite": "💎 Gemini 2.0 Flash-Lite"
}
DEFAULT_MODEL = "gemini-2.0-flash"

# ============================================
# دالة المحادثة
# ============================================
def chat_with_gemini(message, model=DEFAULT_MODEL):
    if not GEMINI_API_KEY:
        return "⚠️ مفتاح Gemini غير مضبوط"
    if not GEMINI_CLIENT:
        return "⚠️ خطأ في عميل Gemini"
    
    try:
        response = GEMINI_CLIENT.models.generate_content(
            model=model,
            contents=message,
            config={"temperature": 0.7, "max_output_tokens": 1024}
        )
        return response.text if response else "⚠️ لا يوجد رد"
    except Exception as e:
        return f"⚠️ خطأ: {str(e)[:100]}"

# ============================================
# القالب الرئيسي
# ============================================
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مروم FM - Gemini AI</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Cairo',sans-serif;background:#0a0a2a;color:#fff;min-height:100vh}
        .navbar{background:#1a1a3a;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #4285f4}
        .logo{font-size:1.5rem;font-weight:800;background:linear-gradient(135deg,#4285f4,#ea4335);-webkit-background-clip:text;background-clip:text;color:transparent}
        .container{max-width:1200px;margin:0 auto;padding:2rem}
        .card{background:#1a1a3a;border-radius:28px;padding:1.5rem;margin-bottom:1.5rem;border:1px solid #4285f4}
        .card h2{color:#4285f4;margin-bottom:1rem}
        .chat-container{display:flex;flex-direction:column;height:500px}
        .chat-messages{flex:1;overflow-y:auto;padding:1rem;background:#0f0f2a;border-radius:20px;margin-bottom:1rem}
        .message{margin-bottom:1rem;padding:1rem;border-radius:20px;max-width:85%}
        .message.user{background:#4285f422;border-right:3px solid #4285f4;margin-right:auto;text-align:right}
        .message.assistant{background:#ea433522;border-left:3px solid #ea4335;margin-left:auto;text-align:left}
        .chat-input{display:flex;gap:0.8rem}
        .chat-input textarea{flex:1;padding:1rem;border-radius:20px;background:#0f0f2a;color:#fff;border:1px solid #4285f4;resize:none}
        .chat-input button{background:linear-gradient(135deg,#4285f4,#ea4335);border:none;border-radius:20px;padding:0 2rem;cursor:pointer;font-weight:bold}
        .footer{text-align:center;padding:1.5rem;color:#888;font-size:0.8rem}
        @media (max-width:768px){.container{padding:1rem}}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">🎙️ مروم FM | Gemini AI</div>
    </nav>
    <div class="container">
        <div class="card">
            <h2>💬 محادثة ذكية</h2>
            <div class="chat-container">
                <div class="chat-messages" id="chatMessages">
                    <div class="message assistant"><strong>🎙️ مروم FM</strong><p>مرحباً! أنا مدعوم من Google Gemini. كيف يمكنني مساعدتك؟</p></div>
                </div>
                <div class="chat-input">
                    <textarea id="messageInput" rows="2" placeholder="اكتب رسالتك..."></textarea>
                    <button onclick="sendMessage()">إرسال</button>
                </div>
            </div>
        </div>
    </div>
    <div class="footer"><p>© 2026 مروم FM | مدعوم من Google Gemini AI</p></div>
    <script>
        async function sendMessage(){
            const input=document.getElementById('messageInput'),msg=input.value.trim();
            if(!msg)return;
            const msgs=document.getElementById('chatMessages');
            msgs.innerHTML+=`<div class="message user"><strong>👤 أنت</strong><p>${escapeHtml(msg)}</p></div>`;
            input.value='';msgs.scrollTop=msgs.scrollHeight;
            msgs.innerHTML+=`<div class="message assistant" id="loading"><strong>🎙️ مروم FM</strong><p>🤔 جاري التفكير مع Gemini...</p></div>`;
            msgs.scrollTop=msgs.scrollHeight;
            try{
                const res=await fetch('/chat/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
                const data=await res.json();
                document.getElementById('loading')?.remove();
                msgs.innerHTML+=`<div class="message assistant"><strong>🎙️ مروم FM</strong><p>${escapeHtml(data.reply)}</p></div>`;
                msgs.scrollTop=msgs.scrollHeight;
            }catch(e){
                document.getElementById('loading')?.remove();
                msgs.innerHTML+=`<div class="message assistant"><strong>🎙️ مروم FM</strong><p>❌ خطأ</p></div>`;
            }
        }
        function escapeHtml(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
        document.getElementById('messageInput').addEventListener('keypress',function(e){if(e.key==='Enter'){e.preventDefault();sendMessage();}});
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
    message = data.get('message', '')
    model = data.get('model', DEFAULT_MODEL)
    if not message:
        return jsonify({"reply": "الرجاء كتابة رسالة"}), 200
    reply = chat_with_gemini(message, model)
    return jsonify({"reply": reply})

# ============================================
# مسار المراقبة (لخدمات UptimeRobot وغيرها)
# ============================================
@app.route('/health')
def health_check():
    """مسار للمراقبة - يعيد حالة الخادم"""
    return jsonify({
        "status": "ok",
        "service": "Maroom FM - Gemini AI",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(GEMINI_API_KEY)
    }), 200

# ============================================
# مسار التوثيق (اختياري)
# ============================================
@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        "status": "healthy",
        "api_key_configured": bool(GEMINI_API_KEY),
        "service": "Google Gemini AI",
        "time": datetime.now().isoformat()
    })

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    print("🎙️ بدء تشغيل مروم FM مع Gemini AI...")
    print(f"🔑 مفتاح Gemini: {'موجود ✅' if GEMINI_API_KEY else 'غير موجود ❌'}")
    print(f"📡 رابط المراقبة: https://kruri.qzz.io/health")
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
