import telebot
import os
import schedule
import time
import threading
import ccxt
import yfinance as yf
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# إعدادات الاتصال
load_dotenv()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
CHANNEL_ID = os.getenv('CHANNEL_ID')
exchange = ccxt.binance()

# دالة حساب المؤشرات يدوياً (للاستغناء عن مكتبات خارجية إضافية)
def calculate_indicators(df):
    # حساب EMA 200
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    # حساب RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# محرك التحليل (الأسواق الحقيقية فقط)
def analyze_market(symbol, market_type):
    try:
        if market_type == 'crypto':
            bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        else:
            df = yf.download(symbol, period="5d", interval="15m", progress=False)
            df.rename(columns={'Close': 'close'}, inplace=True)
        
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        if last['close'] > last['EMA_200'] and last['RSI'] < 40:
            return "BUY"
        elif last['close'] < last['EMA_200'] and last['RSI'] > 60:
            return "SELL"
    except:
        return None

def job():
    assets = [{'s': 'BTC/USDT', 't': 'crypto'}, {'s': 'EURUSD=X', 't': 'forex'}]
    for asset in assets:
        action = analyze_market(asset['s'], asset['t'])
        if action:
            bot.send_message(CHANNEL_ID, f"🚀 إشارة {action} على {asset['s']}")

if __name__ == "__main__":
    schedule.every(15).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)