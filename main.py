import telebot
import os
import time
import ccxt
import yfinance as yf
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
CHANNEL_ID = os.getenv('CHANNEL_ID')
crypto_ex = ccxt.binance()

# القائمة الشاملة (60 أصل)
assets = [
    # كريبتو
    {'s': 'BTC/USDT', 't': 'crypto'}, {'s': 'ETH/USDT', 't': 'crypto'}, {'s': 'SOL/USDT', 't': 'crypto'},
    {'s': 'BNB/USDT', 't': 'crypto'}, {'s': 'XRP/USDT', 't': 'crypto'}, {'s': 'ADA/USDT', 't': 'crypto'},
    {'s': 'DOGE/USDT', 't': 'crypto'}, {'s': 'DOT/USDT', 't': 'crypto'}, {'s': 'MATIC/USDT', 't': 'crypto'},
    {'s': 'LTC/USDT', 't': 'crypto'}, {'s': 'TRX/USDT', 't': 'crypto'}, {'s': 'AVAX/USDT', 't': 'crypto'},
    {'s': 'LINK/USDT', 't': 'crypto'}, {'s': 'SHIB/USDT', 't': 'crypto'}, {'s': 'ATOM/USDT', 't': 'crypto'},
    # فوركس
    {'s': 'EURUSD=X', 't': 'forex'}, {'s': 'GBPUSD=X', 't': 'forex'}, {'s': 'USDJPY=X', 't': 'forex'},
    {'s': 'USDCHF=X', 't': 'forex'}, {'s': 'AUDUSD=X', 't': 'forex'}, {'s': 'NZDUSD=X', 't': 'forex'},
    {'s': 'USDCAD=X', 't': 'forex'}, {'s': 'EURGBP=X', 't': 'forex'}, {'s': 'EURJPY=X', 't': 'forex'},
    {'s': 'GBPJPY=X', 't': 'forex'}, {'s': 'AUDJPY=X', 't': 'forex'}, {'s': 'CHFJPY=X', 't': 'forex'},
    {'s': 'EURCAD=X', 't': 'forex'}, {'s': 'CADJPY=X', 't': 'forex'}, {'s': 'NZDJPY=X', 't': 'forex'},
    # أسهم
    {'s': 'AAPL', 't': 'stocks'}, {'s': 'TSLA', 't': 'stocks'}, {'s': 'NVDA', 't': 'stocks'},
    {'s': 'MSFT', 't': 'stocks'}, {'s': 'GOOGL', 't': 'stocks'}, {'s': 'AMZN', 't': 'stocks'},
    {'s': 'META', 't': 'stocks'}, {'s': 'AMD', 't': 'stocks'}, {'s': 'NFLX', 't': 'stocks'},
    {'s': 'JPM', 't': 'stocks'}, {'s': 'V', 't': 'stocks'}, {'s': 'BAC', 't': 'stocks'},
    {'s': 'DIS', 't': 'stocks'}, {'s': 'PFE', 't': 'stocks'}, {'s': 'KO', 't': 'stocks'},
    # مواد خام
    {'s': 'GC=F', 't': 'comm'}, {'s': 'SI=F', 't': 'comm'}, {'s': 'CL=F', 't': 'comm'},
    {'s': 'NG=F', 't': 'comm'}, {'s': 'ZC=F', 't': 'comm'}, {'s': 'ZS=F', 't': 'comm'},
    {'s': 'ZW=F', 't': 'comm'}, {'s': 'HG=F', 't': 'comm'}, {'s': 'PL=F', 't': 'comm'},
    {'s': 'PA=F', 't': 'comm'}, {'s': 'SB=F', 't': 'comm'}, {'s': 'KC=F', 't': 'comm'},
    {'s': 'CT=F', 't': 'comm'}, {'s': 'ZO=F', 't': 'comm'}, {'s': 'ZM=F', 't': 'comm'}
]

def calculate_indicators(df):
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def analyze(asset):
    try:
        if asset['t'] == 'crypto':
            bars = crypto_ex.fetch_ohlcv(asset['s'], timeframe='15m', limit=250)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        else:
            df = yf.download(asset['s'], period="5d", interval="15m", progress=False)
            df.rename(columns={'Close': 'close'}, inplace=True)
        
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        if last['close'] > last['EMA_200'] and last['RSI'] < 40:
            return "🚀 شراء (Buy)"
        elif last['close'] < last['EMA_200'] and last['RSI'] > 60:
            return "📉 بيع (Sell)"
    except: return None

def run_bot():
    # نظام التناوب: فحص 10 أصول في كل مرة
    batch_size = 10
    while True:
        for i in range(0, len(assets), batch_size):
            batch = assets[i:i+batch_size]
            for asset in batch:
                action = analyze(asset)
                if action:
                    bot.send_message(CHANNEL_ID, f"{action} | الزوج: {asset['s']}")
                time.sleep(2) # تأخير بسيط لتجنب الحظر
            time.sleep(600) # انتظار 10 دقائق قبل البدء بالمجموعة التالية

if __name__ == "__main__":
    run_bot()