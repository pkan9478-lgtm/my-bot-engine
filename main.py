import os
import uuid
import time
import sqlite3
import logging
import threading
import google.generativeai as genai
from flask import Flask, jsonify
from flask_cors import CORS
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ==============================================================================
# SOVEREIGN AUTO-MARKETER (TELEGRAM + BLOGSPOT INTEGRATION)
# ==============================================================================

# [1] လျှို့ဝှက်သော့များ (သင့်၏ Key အစစ်များကို ဤနေရာတွင် ထည့်ပါ)
TELEGRAM_TOKEN = "8391208718:AAEzdJd0pdOdVFbqXr88Oh82IpRheUlqxok" 
GEMINI_API_KEY = "AIzaSyC_zq1RlMZz93jYUm1vefzOU6m9v3lEcJY"

# သင့်၏ Blogspot စာမျက်နှာ လင့်ခ်အစစ်
BLOGSPOT_URL = "https://heinpyisoe.blogspot.com/p/copywriter-portal.html" 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MARKETER CORE] - %(message)s')
logger = logging.getLogger(__name__)

# AI ချိတ်ဆက်ခြင်း (Error မတက်သော gemini-pro ကို အသုံးပြုထားသည်)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro') 

# [2] Database တည်ဆောက်ခြင်း
def init_db():
    conn = sqlite3.connect('sovereign_copywriter.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS copy_sessions (
            session_id TEXT PRIMARY KEY,
            copy_text TEXT,
            created_at REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# FLASK API SERVER (Blogspot မှ လှမ်းချိတ်ရန်)
# ==============================================================================

app = Flask(__name__)
CORS(app) # လုံခြုံရေးကျော်ဖြတ်ရန် CORS ဖွင့်ထားခြင်း

@app.route('/api/get_copy/<session_id>', methods=['GET'])
def get_copy(session_id):
    conn = sqlite3.connect('sovereign_copywriter.db')
    cursor = conn.cursor()
    cursor.execute("SELECT copy_text FROM copy_sessions WHERE session_id=?", (session_id,))
    result = cursor.fetchone()
    
    if result:
        copy_data = result[0]
        cursor.execute("DELETE FROM copy_sessions WHERE session_id=?", (session_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "copy_text": copy_data})
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Link expired or invalid ID."}), 404

def run_flask():
    # Render ၏ Port ကို အလိုအလျောက် ရယူခြင်း
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# ==============================================================================
# TELEGRAM BOT COMMAND CENTER
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👑 **Sovereign AI Marketer မှ ကြိုဆိုပါတယ်။**\n\n"
        "သင်သည် ဤစနစ်ကို **အခမဲ့၊ အကန့်အသတ်မရှိ** အသုံးပြုနိုင်ပါသည်။\n\n"
        "👉 သင်ရောင်းချလိုသော **ပစ္စည်းအမည်နှင့် ဈေးနှုန်း** (ဥပမာ - iPhone 15 Pro Max, 35 သိန်း) ကို စာရိုက်ထည့်လိုက်ပါ။ "
        "ဖောက်သည်များကို ချက်ချင်းဝယ်ချင်စိတ်ပေါက်စေမည့် Professional အရောင်းစာသား (Sales Copy) ကို ဖန်တီးပေးပါမည်။"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def generate_sales_copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    session_id = str(uuid.uuid4())

    wait_msg = await update.message.reply_text("⏳ ဈေးကွက်ကို ထိုးဖောက်မည့် အရောင်းစာသား ဖန်တီးနေပါသည်... စောင့်ပါ။")

    system_instruction = f"""
    သင်သည် အလွန်တော်သော Digital Marketer တစ်ဦးဖြစ်သည်။ 
    အောက်ပါ ပစ္စည်းအချက်အလက်ကို အသုံးပြု၍ Facebook ပေါ်တွင် လူတွေ ချက်ချင်းဝယ်ချင်စိတ်ပေါက်သွားစေမည့် 
    ဆွဲဆောင်မှုရှိသော အရောင်းစာသား (Sales Post) တစ်ခုကို မြန်မာဘာသာဖြင့် ရေးပေးပါ။
    အီမိုဂျီ (Emojis) များ ထည့်သွင်းပြီး၊ အဆုံးတွင် ဝယ်ယူရန် တိုက်တွန်းချက် (Call to Action) ထည့်ပါ။
    
    ပစ္စည်းအချက်အလက်: {user_prompt}
    """

    try:
        response = model.generate_content(system_instruction)
        copy_text = response.text.strip()

        conn = sqlite3.connect('sovereign_copywriter.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO copy_sessions (session_id, copy_text, created_at) VALUES (?, ?, ?)",
                       (session_id, copy_text, time.time()))
        conn.commit()
        conn.close()

        unlock_url = f"{BLOGSPOT_URL}?id={session_id}"
        
        reply_text = (
            f"✅ သင့်အတွက် အရောင်းစာသား အသင့်ဖြစ်နေပါပြီ။\n\n"
            f"အောက်ပါလင့်ခ်သို့ဝင်ရောက်၍ Copy အပြည့်အစုံကို ကူးယူ (Copy) ပါ:\n"
            f"👉 {unlock_url}"
        )
        await wait_msg.edit_text(reply_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"AI Error: {e}")
        await wait_msg.edit_text("❌ စနစ် အလုပ်များနေပါသည်။ ပြန်လည်ကြိုးစားပါ။")

if __name__ == "__main__":
    logger.info("🛡️ Initiating Ad-Driven API Core...")
    web_thread = threading.Thread(target=run_flask)
    web_thread.daemon = True
    web_thread.start()

    logger.info("🛡️ Telegram Engine Online.")
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_sales_copy))
    bot_app.run_polling()

