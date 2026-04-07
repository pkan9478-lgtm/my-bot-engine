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
# STRICT NO-PAYWALL / 100% AD-DRIVEN ARCHITECTURE
# ==============================================================================

# [1] Configuration Keys
TELEGRAM_TOKEN = "8202884575:AAHsd4JxSMfeh11Qtm71FIOflKKFRxlN6TU"
GEMINI_API_KEY = "AIzaSyBzPChxfKn6qCHI9GI6CVPc--I99OgVbjE"

# သင့်၏ Blogspot စာမျက်နှာ လင့်ခ်အစစ်ကို ထည့်ပါ
BLOGSPOT_URL = "https://heinpyisoe.blogspot.com/p/copywriter-portal.html?m=1" 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MARKETER CORE] - %(message)s')
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Copywriting အတွက် အမြန်ဆုံး Model

# [2] Database Setup
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
# THE FLASK API (Blogspot မှ လှမ်းချိတ်မည့် တံခါးပေါက်)
# ==============================================================================

app = Flask(__name__)
CORS(app) # Blogspot မှ Data ဆွဲယူခွင့်ပြုရန် CORS ဖွင့်ထားခြင်း

@app.route('/api/get_copy/<session_id>', methods=['GET'])
def get_copy(session_id):
    """Blogspot မှ ၁၅ စက္ကန့်ပြည့်လျှင် ဤနေရာသို့ လှမ်းတောင်းမည်"""
    conn = sqlite3.connect('sovereign_copywriter.db')
    cursor = conn.cursor()
    cursor.execute("SELECT copy_text FROM copy_sessions WHERE session_id=?", (session_id,))
    result = cursor.fetchone()
    
    if result:
        copy_data = result[0]
        # Data ပေးပြီးသည်နှင့် DB မှ ဖျက်ပစ်မည် (လုံခြုံရေးနှင့် Space သက်သာစေရန်)
        cursor.execute("DELETE FROM copy_sessions WHERE session_id=?", (session_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "copy_text": copy_data})
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Link expired or invalid ID."}), 404

def run_flask():
    app.run(host='0.0.0.0', port=5000, use_reloader=False)

# ==============================================================================
# THE TELEGRAM COMMAND CENTER (အွန်လိုင်းဈေးသည်များ အသုံးပြုရန်)
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
        # AI ဖြင့် အရောင်းစာသားဖန်တီးခြင်း
        response = model.generate_content(system_instruction)
        copy_text = response.text.strip()

        # Database သို့ သိမ်းဆည်းခြင်း
        conn = sqlite3.connect('sovereign_copywriter.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO copy_sessions (session_id, copy_text, created_at) VALUES (?, ?, ?)",
                       (session_id, copy_text, time.time()))
        conn.commit()
        conn.close()

        # Blogspot သို့ သွားရန် Link ထုတ်ပေးခြင်း (?id= ဖြင့် ချိတ်ဆက်သည်)
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