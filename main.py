import telebot
import os
import schedule
import time
import threading
from dotenv import load_dotenv

# 1. تحميل الإعدادات
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

bot = telebot.TeleBot(BOT_TOKEN)

# دالة إرسال الإشارة (التنسيق)
def send_signal(symbol, timeframe, entry, tp, sl, trend, signal_status):
    message_text = f"""
🚀 **VEROLA SIGNAL**
➖➖➖➖➖➖➖➖
📈 **{symbol}** | **{timeframe}**

💰 **Entry:** {entry}
🎯 **TP:** {tp}
🛡 **SL:** {sl}
📈 **Trend:** {trend}

💡 **Suggested Lot Size:**
• $100 - $500 → **0.01**
• $501 - $1,000 → **0.05**
• $1,000+ → **0.10**

⚠️ *Not financial advice. DYOR.*
"""
    bot.send_message(CHANNEL_ID, message_text, parse_mode="Markdown")

# دالة العمل التلقائي
def job_auto_signal():
    print("Running automated analysis...")
    # هنا يتم استدعاء منطق التحليل الخاص بك
    send_signal("BTC/USDT", "5m", "65000", "66000", "64000", "Bullish", "BUY")

# 2. الأوامر اليدوية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً! بوت VerolaSignal يعمل الآن تلقائياً.")

@bot.message_handler(commands=['signal'])
def handle_signal_command(message):
    bot.reply_to(message, "جاري جلب الإشارة يدوياً...")
    send_signal("BTC/USDT", "5m", "65000", "66000", "64000", "Bullish", "BUY")

# 3. التشغيل الرئيسي (الجدولة + البوت)
if __name__ == "__main__":
    # جدولة المهمة التلقائية كل 5 دقائق
    schedule.every(5).minutes.do(job_auto_signal)
    
    # دالة لتشغيل الجدول الزمني في الخلفية
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # تشغيل البوت الأساسي
    print("Bot is running...")
    bot.remove_webhook()
    bot.polling(none_stop=True)