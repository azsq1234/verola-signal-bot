import os
import telebot
import ccxt
import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client
from dotenv import load_dotenv

# تحميل المتغيرات السرية
load_dotenv()

# إعدادات الاتصال
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# قائمة الأصول (مثال مصغر لـ 60 أصلاً)
assets = ['BTC/USDT', 'ETH/USDT', 'AAPL', 'GOOGL', 'TSLA', 'EURUSD=X', 'GC=F'] # أضف باقي الـ 60 هنا

def save_to_db(symbol, action):
    try:
        data = {"symbol": symbol, "signal_type": action}
        supabase.table("signals").insert(data).execute()
        print(f"✅ تم حفظ {symbol} في قاعدة البيانات")
    except Exception as e:
        print(f"❌ خطأ في الحفظ في قاعدة البيانات: {e}")

def analyze_asset(symbol):
    # كود جلب البيانات والتحليل (هنا نستخدم المنطق الذي اتفقنا عليه)
    # ... (ضع كود التحليل الخاص بك هنا) ...
    # مثال افتراضي لإشارة:
    action = "🚀 شراء (Buy)" 
    
    # إرسال لتليجرام
    bot.send_message(CHANNEL_ID, f"إشارة جديدة لـ {symbol}: {action}")
    
    # حفظ في Supabase
    save_to_db(symbol, action)

# تشغيل البوت
if __name__ == "__main__":
    for asset in assets:
        analyze_asset(asset)