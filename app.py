from flask import Flask, render_template_string, request, jsonify, Response
from flask_cors import CORS
import os
import requests
from datetime import datetime
from urllib.parse import quote

# ============================================
# تهيئة التطبيق
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'maroom-secret-key-2026')
CORS(app)

# إعدادات Groq API
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# نماذج Groq المتاحة
AVAILABLE_MODELS = {
    "llama-3.3-70b-versatile": "🚀 Groq Llama 3.3 70B (الأفضل)",
    "llama-3.1-8b-instant": "⚡ Groq Llama 3.1 8B (الأسرع)",
    "mixtral-8x7b-32768": "🧠 Groq Mixtral 8x7B (دقيق)",
    "llama3-70b-8192": "🦙 Groq Llama 3 70B",
    "gemma2-9b-it": "💎 Google Gemma 2 9B"
}
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# ============================================
# دالة المحادثة مع Groq
# ============================================
def chat_with_groq(message, model=DEFAULT_MODEL):
    """الاتصال بـ Groq API وإرجاع الرد"""
    
    if not GROQ_API_KEY:
        return "⚠️ عذراً، مفتاح Groq غير مضبوط. يرجى إضافة GROQ_API_KEY في المتغيرات البيئية."
    
    if not GROQ_API_KEY.startswith('gsk_'):
        return "⚠️ مفتاح Groq غير صالح. يجب أن يبدأ بـ gsk_"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 0.9
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            error_detail = response.json() if response.text else {}
            error_msg = error_detail.get('error', {}).get('message', str(response.status_code))
            return f"⚠️ خطأ تقني: {error_msg}"
            
    except requests.exceptions.Timeout:
        return "⚠️ انتهت المهلة. يرجى المحاولة مرة أخرى."
    except requests.exceptions.ConnectionError:
        return "⚠️ فشل الاتصال. تحقق من اتصالك بالإنترنت."
    except Exception as e:
        return f"⚠️ خطأ: {str(e)[:100]}"

# ============================================
# دالة توليد الصور (مجانية)
# ============================================
def generate_image_with_pollinations(prompt, width=1024, height=1024):
    """توليد صورة باستخدام Pollinations.ai"""
    try:
        encoded_prompt = quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}"
        response = requests.get(image_url, timeout=60)
        if response.status_code == 200:
            return response.content, None
        else:
            return None, f"فشل التوليد: {response.status_code}"
    except Exception as e:
        return None, f"خطأ: {str(e)}"

# ============================================
# القالب الرئيسي (HTML كامل)
# ============================================
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مروم FM - ذكاء اصطناعي</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Cairo','Segoe UI',sans-serif;background:#0a0a2a;color:#fff;min-height:100vh}
        .navbar{background:#1a1a3a;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #ff6b00}
        .logo{font-size:1.5rem;font-weight:800;background:linear-gradient(135deg,#ff6b00,#ff2b7a);-webkit-background-clip:text;background-clip:text;color:transparent}
        .container{max-width:1200px;margin:0 auto;padding:2rem}
        .card{background:#1a1a3a;border-radius:28px;padding:1.5rem;margin-bottom:1.5rem;border:1px solid #ff6b00}
        .card h2{color:#ff6b00;margin-bottom:1rem}
        .chat-container{display:flex;flex-direction:column;height:500px}
        .chat-messages{flex:1;overflow-y:auto;padding:1rem;background:#0f0f2a;border-radius:20px;margin-bottom:1rem}
        .message{margin-bottom:1rem;padding:1rem;border-radius:20px;max-width:85%;animation:fadeIn 0.3s}
        @keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        .message.user{background:#ff6b0022;border-right:3px solid #ff6b00;margin-right:auto;text-align:right}
        .message.assistant{background:#ff2b7a22;border-left:3px solid #ff2b7a;margin-left:auto;text-align:left}
        .chat-input{display:flex;gap:0.8rem}
        .chat-input textarea{flex:1;padding:1rem;border:1px solid #ff6b00;border-radius:20px;background:#0f0f2a;color:#fff;resize:none;font-family:inherit}
        .chat-input textarea:focus{outline:none;border-color:#ff2b7a}
        .chat-input button{background:linear-gradient(135deg,#ff6b00,#ff2b7a);border:none;border-radius:20px;padding:0 2rem;cursor:pointer;font-weight:bold;transition:0.3s}
        .chat-input button:hover{transform:scale(1.02)}
        .tools-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;margin:1rem 0}
        .tool-btn{background:#ff6b0022;border:1px solid #ff6b00;padding:0.8rem;border-radius:16px;cursor:pointer;text-align:center;transition:0.3s}
        .tool-btn:hover{background:#ff6b0044;transform:translateY(-2px)}
        select,textarea{width:100%;padding:0.8rem;margin:0.5rem 0;border:1px solid #ff6b00;border-radius:16px;background:#0f0f2a;color:#fff}
        .result-box{background:#0f0f2a;padding:1rem;border-radius:20px;margin-top:1rem;white-space:pre-wrap}
        .footer{text-align:center;padding:1.5rem;color:#888;font-size:0.8rem}
        a{color:#ff6b00;text-decoration:none}
        img{max-width:100%;border-radius:16px}
        .message-time{font-size:0.7rem;color:#888;margin-top:0.5rem}
        @media (max-width:768px){.container{padding:1rem}.message{max-width:95%}}
        ::-webkit-scrollbar{width:6px}
        ::-webkit-scrollbar-track{background:#0f0f2a}
        ::-webkit-scrollbar-thumb{background:#ff6b00;border-radius:10px}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="logo">🎙️ مروم FM | Groq AI</div>
    </nav>
    <div class="container">
        <div class="card">
            <h2>💬 محادثة ذكية</h2>
            <div class="chat-container">
                <div class="chat-messages" id="chatMessages">
                    <div class="message assistant">
                        <strong>🎙️ مروم FM</strong>
                        <p>مرحباً بك! أنا مدعوم من Groq AI (Llama 3). كيف يمكنني مساعدتك اليوم؟</p>
                        <div class="message-time">الآن</div>
                    </div>
                </div>
                <div class="chat-input">
                    <textarea id="messageInput" rows="2" placeholder="اكتب رسالتك هنا..." onkeypress="handleKeyPress(event)"></textarea>
                    <button onclick="sendMessage()">إرسال ➤</button>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🛠️ أدوات ذكية سريعة</h2>
            <div class="tools-grid">
                <div class="tool-btn" onclick="sendToolMessage('لخص النص التالي: ' + getSelectedText())">📝 تلخيص</div>
                <div class="tool-btn" onclick="sendToolMessage('ترجم النص التالي إلى العربية: ' + getSelectedText())">🌐 ترجمة</div>
                <div class="tool-btn" onclick="sendToolMessage('صحح الأخطاء في النص التالي: ' + getSelectedText())">✍️ تدقيق</div>
                <div class="tool-btn" onclick="sendToolMessage('حلل المشاعر في النص التالي: ' + getSelectedText())">😊 تحليل</div>
                <div class="tool-btn" onclick="sendToolMessage('اقترح 5 أفكار من النص التالي: ' + getSelectedText())">💡 أفكار</div>
            </div>
        </div>
    </div>
    <div class="footer">
        <p>© 2026 مروم FM - جميع الحقوق محفوظة | مدعوم من Groq AI</p>
    </div>
    
    <script>
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function getSelectedText() {
            const text = document.getElementById('messageInput').value;
            if (text) return text;
            return "مروم FM";
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (!message) return;
            
            const msgsDiv = document.getElementById('chatMessages');
            
            // عرض رسالة المستخدم
            msgsDiv.innerHTML += `
                <div class="message user">
                    <strong>👤 أنت</strong>
                    <p>${escapeHtml(message)}</p>
                    <div class="message-time">الآن</div>
                </div>
            `;
            input.value = '';
            msgsDiv.scrollTop = msgsDiv.scrollHeight;
            
            // عرض مؤشر التحميل
            msgsDiv.innerHTML += `
                <div class="message assistant" id="loadingMsg">
                    <strong>🎙️ مروم FM</strong>
                    <p>🤔 جاري التفكير مع Groq...</p>
                    <div class="message-time">الآن</div>
                </div>
            `;
            msgsDiv.scrollTop = msgsDiv.scrollHeight;
            
            try {
                const response = await fetch('/chat/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                
                document.getElementById('loadingMsg')?.remove();
                msgsDiv.innerHTML += `
                    <div class="message assistant">
                        <strong>🎙️ مروم FM</strong>
                        <p>${escapeHtml(data.reply)}</p>
                        <div class="message-time">الآن</div>
                    </div>
                `;
                msgsDiv.scrollTop = msgsDiv.scrollHeight;
            } catch (error) {
                document.getElementById('loadingMsg')?.remove();
                msgsDiv.innerHTML += `
                    <div class="message assistant">
                        <strong>🎙️ مروم FM</strong>
                        <p>❌ عذراً، حدث خطأ تقني. حاول مرة أخرى.</p>
                        <div class="message-time">الآن</div>
                    </div>
                `;
            }
        }
        
        function sendToolMessage(prompt) {
            document.getElementById('messageInput').value = prompt;
            sendMessage();
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
    </script>
</body>
</html>
'''

# ============================================
# المسارات الرئيسية
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
    
    reply = chat_with_groq(message, model)
    return jsonify({"reply": reply})

# ============================================
# مسار المراقبة (لخدمات UptimeRobot)
# ============================================

@app.route('/health')
def health_check():
    """مسار للمراقبة - يعيد حالة الخادم"""
    return jsonify({
        "status": "ok",
        "service": "Maroom FM - Groq AI",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_'))
    }), 200

# ============================================
# مسارات API الخارجية
# ============================================

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        "status": "healthy",
        "api_key_configured": bool(GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_')),
        "default_model": DEFAULT_MODEL,
        "available_models": AVAILABLE_MODELS,
        "service": "Groq AI",
        "time": datetime.now().isoformat()
    })

@app.route('/api/models', methods=['GET'])
def api_models():
    return jsonify(AVAILABLE_MODELS)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """واجهة API للتطبيقات الخارجية"""
    data = request.get_json()
    message = data.get('message', '')
    model = data.get('model', DEFAULT_MODEL)
    
    if not message:
        return jsonify({"error": "الرسالة مطلوبة"}), 400
    
    reply = chat_with_groq(message, model)
    return jsonify({"success": True, "reply": reply})

# ============================================
# مسارات توليد الصور (اختيارية)
# ============================================

@app.route('/api/generate-image', methods=['POST'])
def api_generate_image():
    data = request.get_json()
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({"error": "الوصف مطلوب"}), 400
    image_data, error = generate_image_with_pollinations(prompt)
    if image_data:
        return Response(image_data, mimetype='image/jpeg')
    return jsonify({"error": error}), 500

@app.route('/api/generate-url', methods=['POST'])
def api_generate_url():
    data = request.get_json()
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({"error": "الوصف مطلوب"}), 400
    encoded_prompt = quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
    return jsonify({"success": True, "image_url": image_url})

# ============================================
# التشغيل
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🎙️ بدء تشغيل منصة مروم FM مع Groq API")
    print("=" * 50)
    print(f"🔑 مفتاح Groq: {'موجود ✅' if GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_') else 'غير موجود ❌'}")
    print(f"🧠 النموذج الافتراضي: {DEFAULT_MODEL}")
    print(f"📡 رابط المراقبة: https://kruri.qzz.io/health")
    print(f"📡 رابط API: https://kruri.qzz.io/api/health")
    print("=" * 50)
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
