import telebot
import os
from dotenv import load_dotenv

# 1. تحميل الإعدادات من ملف .env
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# 2. تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# **حل تعارض الاتصال (السطر الذي طلبته)**
# هذا الأمر يقطع أي اتصال ويب-هوك قديم معلق في خوادم تليجرام
bot.remove_webhook()

def send_signal(symbol, timeframe, entry, tp, sl, trend, signal_status):
    # الفلتر: إذا كانت الحالة "HOLD" أو فارغة، لا ترسل شيئاً
    if signal_status.upper() == "HOLD" or not entry or entry == "—":
        print(f"Skipping {symbol}: No active signal.")
        return

    # التنسيق النظيف (الثيم المطلوب)
    message_text = f"""
📡 **VEROLA SIGNAL**
──────────────────────────────
🪙 **{symbol}** |  **{timeframe}**

💰 **Entry:** {entry}
🎯 **TP:** {tp}
🛡️ **SL:** {sl}
📈 **Trend:** {trend}

⚖️ **Suggested Lot Size:**
• $100 – $500    → **0.01**
• $501 – $1,000 → **0.05**
• $1,000+        → **0.10**

⚠️ *Not financial advice. DYOR.*
"""

    # إرسال الرسالة
    try:
        bot.send_message(chat_id=CHANNEL_ID, text=message_text, parse_mode='Markdown')
        print(f"Signal sent successfully for {symbol}")
    except Exception as e:
        print(f"Error sending signal: {e}")

# 3. تشغيل البوت
if __name__ == "__main__":
    print("Bot is starting... (Connected and cleared old sessions)")
    bot.infinity_polling()
