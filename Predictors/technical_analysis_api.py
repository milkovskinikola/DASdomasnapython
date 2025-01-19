import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from pymongo import MongoClient
from flask import jsonify

client = MongoClient("mongodb://localhost:27017/")
db = client["stocks_db"]
collection = db["stock_data"]

def clean_data(value):
    if isinstance(value, str):
        value = value.replace(',', '.')
        value = value.replace('.', '', value.count('.') - 1)
        try:
            return float(value)
        except ValueError:
            return 0
    return value

def fetch_historical_data(stock_code, start_date, end_date):
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = end_date.strftime('%Y-%m-%d')

    query = {"company_name": stock_code, "date": {"$gte": start_date, "$lte": end_date}}
    cursor = collection.find(query)
    data = list(cursor)
    if not data:
        return None

    df = pd.DataFrame(data)
    df['last_trade_price'] = pd.to_numeric(df['last_trade_price'], errors='coerce')
    df['max_price'] = pd.to_numeric(df['max_price'], errors='coerce')
    df['min_price'] = pd.to_numeric(df['min_price'], errors='coerce')

    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)

    for column in ['last_trade_price', 'max_price', 'min_price', 'volume']:
        df[column] = df[column].apply(clean_data)

    return df

def calculate_indicators(data):
    # 1. Calculate RSI (Relative Strength Index)
    def calculate_rsi(data, period=14):
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    # 2. Calculate Stochastic Oscillator (STOCH_K and STOCH_D)
    def calculate_stoch(data, period=14):
        low_min = data['min_price'].rolling(window=period).min()
        high_max = data['max_price'].rolling(window=period).max()

        stoch_k = 100 * ((data['last_trade_price'] - low_min) / (high_max - low_min))
        stoch_d = stoch_k.rolling(window=3).mean()

        return stoch_k, stoch_d

    # 3. Calculate MACD (Moving Average Convergence Divergence)
    def calculate_macd(data, short_period=12, long_period=26, signal_period=9):
        ema_short = data['last_trade_price'].ewm(span=short_period, adjust=False).mean()
        ema_long = data['last_trade_price'].ewm(span=long_period, adjust=False).mean()

        macd = ema_short - ema_long
        signal = macd.ewm(span=signal_period, adjust=False).mean()

        return macd, signal

    # 4. Calculate SMA (Simple Moving Average)
    def calculate_sma(data, period=30):
        return data['last_trade_price'].rolling(window=period).mean()

    # 5. Calculate EMA (Exponential Moving Average)
    def calculate_ema(data, period=30):
        return data['last_trade_price'].ewm(span=period, adjust=False).mean()

    # Calculate all indicators
    data['RSI'] = calculate_rsi(data['last_trade_price'])
    data['STOCH_K'], data['STOCH_D'] = calculate_stoch(data)
    data['MACD'], data['MACD_SIGNAL'] = calculate_macd(data)
    data['SMA'] = calculate_sma(data)
    data['EMA'] = calculate_ema(data)

    # Generate signals
    data['RSI_SIGNAL'] = data['RSI'].apply(lambda x: 'BUY' if x < 30 else ('SELL' if x > 70 else 'HOLD'))
    data['STOCH_SIGNAL'] = data['STOCH_K'].apply(lambda x: 'BUY' if x < 20 else ('SELL' if x > 80 else 'HOLD'))
    data['MACD_SIGNAL'] = data['MACD'].apply(lambda x: 'BUY' if x > 0 else 'SELL')
    data['SMA_SIGNAL'] = data.apply(lambda row: 'BUY' if row['last_trade_price'] > row['SMA'] else ('SELL' if row['last_trade_price'] < row['SMA'] else 'HOLD'), axis=1)
    data['EMA_SIGNAL'] = data.apply(lambda row: 'BUY' if row['last_trade_price'] > row['EMA'] else ('SELL' if row['last_trade_price'] < row['EMA'] else 'HOLD'), axis=1)

    return data


def analyze_stock(stock_code, timeperiod=30):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 2)

        df = fetch_historical_data(stock_code, start_date, end_date)
        if df is None:
            return jsonify({"status": "error", "message": f"No data found for stock code {stock_code}"}), 404

        df = calculate_indicators(df)

        all_together_result = df.iloc[-1] 

        aggregated_result = {
            "stock_code": stock_code,  # Use the actual stock code
            "date_range": f"{df.index.min().strftime('%d.%m.%Y')} - {df.index.max().strftime('%d.%m.%Y')}",
            "last_price": float(df['last_trade_price'].iloc[-1]),
            "SMA_1": float(df['SMA'].iloc[-1]),
            "EMA_1": float(df['EMA'].iloc[-1]),
            "RSI": float(df['RSI'].iloc[-1]),
            "MACD": float(df['MACD'].iloc[-1]),
            "STOCH": float(df['STOCH_K'].iloc[-1]),
            "Signal": df['RSI_SIGNAL'].iloc[-1],
            "RSI_SIGNAL": df['RSI_SIGNAL'].iloc[-1],
            "STOCH_SIGNAL": df['STOCH_SIGNAL'].iloc[-1],
            "MACD_SIGNAL": df['MACD_SIGNAL'].iloc[-1],
            "SMA_SIGNAL": df['SMA_SIGNAL'].iloc[-1],
            "EMA_SIGNAL": df['EMA_SIGNAL'].iloc[-1],
            "WMA_SIGNAL": df['WMA_SIGNAL'].iloc[-1] if 'WMA_SIGNAL' in df.columns else None,
            "TRIMA_SIGNAL": df['TRIMA_SIGNAL'].iloc[-1] if 'TRIMA_SIGNAL' in df.columns else None,
            "KAMA_SIGNAL": df['KAMA_SIGNAL'].iloc[-1] if 'KAMA_SIGNAL' in df.columns else None
        }
        return aggregated_result

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
