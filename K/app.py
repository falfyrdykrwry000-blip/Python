"""
بوت تليجرام ذكي - مروم FM
متصل مع Groq API للردود الذكية
"""

import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from datetime import datetime
import json

# ============================================
# الإعدادات
# ============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغيرات البيئة
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://krar.dpdns.org')

# إعدادات Groq API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# إعدادات Flask
app = Flask(__name__)

# تهيئة البوت (سيتم لاحقاً)
application = None

# ============================================
# دوال الذكاء الاصطناعي
# ============================================

def chat_with_groq(message, model="llama-3.3-70b-versatile"):
    """الاتصال بـ Groq API والحصول على رد ذكي"""
    
    if not GROQ_API_KEY:
        return "⚠️ عذراً، مفتاح Groq غير مضبوط. يرجى التواصل مع الدعم."
    
    if not GROQ_API_KEY.startswith('gsk_'):
        return "⚠️ مفتاح Groq غير صالح."
    
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
            error_msg = response.json().get('error', {}).get('message', str(response.status_code))
            return f"⚠️ خطأ تقني: {error_msg}"
            
    except requests.exceptions.Timeout:
        return "⚠️ انتهت المهلة. يرجى المحاولة مرة أخرى."
    except Exception as e:
        return f"⚠️ خطأ: {str(e)[:100]}"


# ============================================
# دوال البوت
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /start"""
    user = update.effective_user
    welcome_message = f"""
🎙️ **مرحباً بك في بوت مروم FM الذكي!**

أهلاً {user.first_name} 👋

أنا بوت ذكي يعمل بتقنية **Groq AI** (Llama 3.3 70B). يمكنني:

✅ الإجابة على أسئلتك  
✅ مساعدتك في البحث والتحليل  
✅ الترفيه عنك بالنكات والمعلومات  
✅ مساعدتك في المهام اليومية  

📌 **الأوامر المتاحة:**
/start - عرض هذه الرسالة  
/help - عرض المساعدة  
/about - معلومات عن البوت  
/models - عرض النماذج المتاحة  
/model_groq - استخدام نموذج Groq السريع  
/model_llama - استخدام نموذج Llama المتقدم  

✨ **أو فقط اكتب سؤالك وسأجيبك فوراً!**

---
© 2026 مروم FM - ذكاء اصطناعي متقدم
"""
    
    keyboard = [
        [InlineKeyboardButton("❓ مساعدة", callback_data='help'),
         InlineKeyboardButton("ℹ️ عن البوت", callback_data='about')],
        [InlineKeyboardButton("🧠 نموذج Groq", callback_data='model_groq'),
         InlineKeyboardButton("🦙 نموذج Llama", callback_data='model_llama')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /help"""
    help_text = """
❓ **كيف أستخدم بوت مروم FM؟**

**📝 الأوامر الأساسية:**
• `/start` - بدء المحادثة
• `/help` - عرض هذه المساعدة
• `/about` - معلومات عن البوت
• `/models` - عرض النماذج المتاحة

**💬 طريقة الاستخدام:**
• اكتب سؤالك مباشرة وسأجيبك
• استخدم الأزرار التفاعلية للتنقل

**🎯 أمثلة على الأسئلة:**
• ما هو الذكاء الاصطناعي؟
• اشرح لي نظرية النسبية
• أخبرني نكتة مضحكة
• كيف أتعلم البرمجة؟
• ما هي عاصمة فرنسا؟

**⚡ ملاحظة:** البوت متصل مع Groq AI، مما يعني ردود سريعة وذكية!

---
أرسل سؤالك الآن وسأجيبك فوراً ✨
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /about"""
    about_text = """
ℹ️ **عن بوت مروم FM**

**الاسم:** مروم FM بوت ذكي  
**الإصدار:** 2.0.0  
**التقنيات:** Python + Flask + Groq API + Telegram API  

**المميزات:**
• 🧠 ذكاء اصطناعي متقدم (Llama 3.3 70B)
• ⚡ ردود سريعة جداً (Groq LPU)
• 🌐 دعم كامل للغة العربية
• 🔄 متاح 24/7
• 💬 محادثة طبيعية وذكية

**النماذج المدعومة:**
• `llama-3.3-70b-versatile` - الأقوى والأدق
• `llama-3.1-8b-instant` - الأسرع
• `mixtral-8x7b-32768` - متعدد الاستخدامات

**المطور:** مروم FM  
**النطاق:** krar.dpdns.org

---
شكراً لاستخدامك البوت! 💙
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')


async def show_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض النماذج المتاحة"""
    models_text = """
🧠 **النماذج المتاحة للذكاء الاصطناعي:**

• `llama-3.3-70b-versatile` - **Llama 3.3 70B**  
  الأقوى والأدق، مناسب للمهام المعقدة

• `llama-3.1-8b-instant` - **Llama 3.1 8B**  
  الأسرع، مناسب للمحادثات السريعة

• `mixtral-8x7b-32768` - **Mixtral 8x7B**  
  ممتاز للمهام المتعددة

**لتغيير النموذج الحالي، استخدم الأمر:**  
`/model_groq` أو `/model_llama`

**النموذج الحالي:** `{}`
""".format(context.user_data.get('model', 'llama-3.3-70b-versatile'))
    
    await update.message.reply_text(models_text, parse_mode='Markdown')


async def set_model_groq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعيين نموذج Groq السريع"""
    context.user_data['model'] = 'llama-3.1-8b-instant'
    await update.message.reply_text("✅ تم تعيين النموذج إلى **Groq Llama 3.1 8B** (الأسرع)", parse_mode='Markdown')


async def set_model_llama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعيين نموذج Llama المتقدم"""
    context.user_data['model'] = 'llama-3.3-70b-versatile'
    await update.message.reply_text("✅ تم تعيين النموذج إلى **Llama 3.3 70B** (الأقوى والأدق)", parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المستخدم والرد بذكاء"""
    user_message = update.message.text
    user_name = update.effective_user.first_name
    
    # تجاهل الأوامر
    if user_message.startswith('/'):
        return
    
    # الحصول على النموذج المختار (افتراضي: Llama 3.3 70B)
    model = context.user_data.get('model', 'llama-3.3-70b-versatile')
    
    # إظهار مؤشر الكتابة
    await update.message.chat.send_action(action="typing")
    
    # إرسال إشارة أن البوت يفكر
    thinking_msg = await update.message.reply_text("🤔 **جاري التفكير...**", parse_mode='Markdown')
    
    # الحصول على الرد من Groq API
    reply = chat_with_groq(user_message, model)
    
    # حذف رسالة "جاري التفكير"
    await thinking_msg.delete()
    
    # إرسال الرد
    await update.message.reply_text(reply, parse_mode='Markdown')


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار التفاعلية"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        await help_command(update, context)
    elif query.data == 'about':
        await about(update, context)
    elif query.data == 'model_groq':
        await set_model_groq(update, context)
    elif query.data == 'model_llama':
        await set_model_llama(update, context)
    
    await query.edit_message_reply_markup(reply_markup=None)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ عذراً، حدث خطأ تقني. يرجى المحاولة مرة أخرى لاحقاً.")


# ============================================
# إعداد البوت
# ============================================

def setup_bot():
    """تهيئة البوت وإضافة المعالجات"""
    global application
    
    if not TOKEN:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN غير مضبوط")
        return None
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("models", show_models))
    application.add_handler(CommandHandler("model_groq", set_model_groq))
    application.add_handler(CommandHandler("model_llama", set_model_llama))
    
    # معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالج الأزرار التفاعلية
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    logger.info("✅ تم تهيئة البوت بنجاح")
    return application


# ============================================
# مسارات Flask (لـ Webhook)
# ============================================

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    return jsonify({
        "status": "ok",
        "service": "Maroom FM Telegram Bot",
        "version": "2.0.0",
        "bot_username": "MaroomFMBot",
        "time": datetime.now().isoformat()
    })


@app.route('/health')
def health():
    """مسار المراقبة"""
    return jsonify({
        "status": "healthy",
        "bot_configured": bool(TOKEN),
        "groq_configured": bool(GROQ_API_KEY),
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    """نقطة استقبال Webhook من تليجرام"""
    if not TOKEN:
        return jsonify({"error": "Bot token not configured"}), 500
    
    try:
        # الحصول على البيانات
        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "No data received"}), 400
        
        # معالجة التحديث
        if application:
            update = Update.de_json(update_data, application.bot)
            asyncio.create_task(application.process_update(update))
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"خطأ في معالجة Webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/set-webhook')
def set_webhook():
    """تعيين Webhook يدوياً"""
    if not TOKEN:
        return "⚠️ التوكن غير مضبوط", 500
    
    import telegram
    bot = telegram.Bot(token=TOKEN)
    webhook_url = f"{RENDER_URL}/webhook/{TOKEN}"
    
    try:
        bot.set_webhook(url=webhook_url)
        return f"""
✅ **تم تعيين Webhook بنجاح!**

📡 **عنوان Webhook:** `{webhook_url}`  
🤖 **البوت:** متصل وجاهز للاستخدام

**جرب البوت الآن على تليجرام!**
"""
    except Exception as e:
        return f"❌ خطأ: {str(e)}", 500


# ============================================
# التشغيل
# ============================================

if __name__ == '__main__':
    # تهيئة البوت
    setup_bot()
    
    # تشغيل الخادم
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 بدء تشغيل خادم بوت مروم FM على المنفذ {port}")
    logger.info(f"🔗 رابط Webhook: https://krar.dpdns.org/webhook/{TOKEN}")
    app.run(host='0.0.0.0', port=port, debug=False)