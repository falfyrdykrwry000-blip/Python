import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from datetime import datetime

# ============================================
# الإعدادات الأساسية
# ============================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://krar.dpdns.org')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

app = Flask(__name__)
application = None

# ============================================
# دوال الذكاء الاصطناعي
# ============================================
def chat_with_groq(message, model="llama-3.3-70b-versatile"):
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith('gsk_'):
        return "⚠️ مفتاح Groq غير مضبوط أو غير صالح."
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {"model": model, "messages": [{"role": "user", "content": message}], "temperature": 0.7, "max_tokens": 1024}
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"⚠️ خطأ: {response.status_code}"
    except Exception as e:
        return f"⚠️ خطأ: {str(e)[:100]}"

# ============================================
# دوال البوت
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("❓ مساعدة", callback_data='help')]]
    await update.message.reply_text("🎙️ مرحباً بك في بوت مروم FM الذكي!\nأرسل أي سؤال وسأجيبك.", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 الأوامر:\n/start - بدء المحادثة\n/help - هذه المساعدة\n/about - معلومات عن البوت")

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ بوت مروم FM | الإصدار 2.0.0 | يعمل بتقنية Groq AI")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith('/'):
        return
    await update.message.chat.send_action(action="typing")
    thinking = await update.message.reply_text("🤔 **جاري التفكير...**", parse_mode='Markdown')
    reply = chat_with_groq(update.message.text)
    await thinking.delete()
    await update.message.reply_text(reply, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'help':
        await help_command(update, context)
    await query.edit_message_reply_markup(reply_markup=None)

def setup_bot():
    global application
    if not TOKEN:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN غير مضبوط")
        return None
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("✅ تم تهيئة البوت")
    return application

# ============================================
# مسارات Flask
# ============================================
@app.route('/')
def home():
    return jsonify({"status": "ok", "service": "Maroom FM Bot"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "bot_configured": bool(TOKEN), "groq_configured": bool(GROQ_API_KEY)}), 200

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    if not application:
        return jsonify({"error": "Bot not initialized"}), 500
    try:
        update = Update.de_json(request.get_json(), application.bot)
        asyncio.run(application.process_update(update))
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"خطأ: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/set-webhook')
def set_webhook():
    try:
        import telegram
        bot = telegram.Bot(token=TOKEN)
        webhook_url = f"{RENDER_URL}/webhook/{TOKEN}"
        bot.set_webhook(url=webhook_url)
        return f"✅ Webhook set to {webhook_url}"
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

# ============================================
# التشغيل
# ============================================
if __name__ == '__main__':
    setup_bot()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)