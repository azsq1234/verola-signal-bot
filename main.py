import telebot
import os
import schedule
import time
import threading
import ccxt
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import feedparser
from textblob import TextBlob
from dotenv import load_dotenv

# إعدادات الاتصال
load_dotenv()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
CHANNEL_ID = os.getenv('CHANNEL_ID')
exchange = ccxt.binance()

# 1. محرك تحليل الأخبار (مجاني ومستقل)
def get_sentiment(symbol):
    try:
        # مصادر أخبار عامة (يمكنك إضافة المزيد من روابط RSS)
        urls = ["https://cointelegraph.com/rss", "https://www.cnbc.com/id/15839063/device/rss/rss.html"]
        sentiment = 0
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                sentiment += TextBlob(entry.title).sentiment.polarity
        return sentiment / len(urls)
    except:
        return 0

# 2. محرك البيانات (كريبتو، فوركس، أسهم)
def get_data(symbol, market_type):
    try:
        if market_type == 'crypto':
            bars = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=200)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        else:
            df = yf.download(symbol, period="5d", interval="5m", progress=False)
            df.reset_index(inplace=True)
            df.rename(columns={'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low'}, inplace=True)
        return df
    except:
        return None

# 3. محرك التحليل الفني (استراتيجية النخبة)
def analyze_market(symbol, market_type):
    df = get_data(symbol, market_type)
    if df is None or len(df) < 200: return None
    
    df['EMA_200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    df = pd.concat([df, macd], axis=1)
    
    last = df.iloc[-1]
    sentiment = get_sentiment(symbol)
    
    # دمج التحليل الفني مع المشاعر (منطق القرار)
    if last['close'] > last['EMA_200'] and last['RSI'] < 40 and sentiment > 0:
        return "BUY"
    elif last['close'] < last['EMA_200'] and last['RSI'] > 60 and sentiment < 0:
        return "SELL"
    return None

# 4. التنفيذ والجدولة
def job():
    assets = [
        {'s': 'BTC/USDT', 't': 'crypto'}, {'s': 'ETH/USDT', 't': 'crypto'},
        {'s': 'EURUSD=X', 't': 'forex'}, {'s': 'AAPL', 't': 'stocks'}
    ]
    for asset in assets:
        action = analyze_market(asset['s'], asset['t'])
        if action:
            bot.send_message(CHANNEL_ID, f"🚀 فرصة {action} على {asset['s']}\n📊 تحليل: فني + مشاعر أخبار.")

if __name__ == "__main__":
    schedule.every(5).minutes.do(job)
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)
    threading.Thread(target=run_scheduler, daemon=True).start()
    bot.polling(none_stop=True)