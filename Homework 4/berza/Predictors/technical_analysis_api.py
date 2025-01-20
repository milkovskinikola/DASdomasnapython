import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from pymongo import MongoClient
from flask import jsonify

class DatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.client = MongoClient("mongodb://mongo:27017/")
            cls._instance.db = cls._instance.client["stocks_db"]
        return cls._instance

    def get_collection(self, collection_name):
        return self.db[collection_name]

class TechnicalAnalysisUtils:
    @staticmethod
    def clean_data(value):
        if isinstance(value, str):
            value = value.replace(',', '.')
            value = value.replace('.', '', value.count('.') - 1)
            try:
                return float(value)
            except ValueError:
                return 0
        return value

    @staticmethod
    def calculate_rsi(data, period=14):
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_stoch(data, period=14):
        low_min = data['min_price'].rolling(window=period).min()
        high_max = data['max_price'].rolling(window=period).max()

        stoch_k = 100 * ((data['last_trade_price'] - low_min) / (high_max - low_min))
        stoch_d = stoch_k.rolling(window=3).mean()

        return stoch_k, stoch_d

    @staticmethod
    def calculate_macd(data, short_period=12, long_period=26, signal_period=9):
        ema_short = data['last_trade_price'].ewm(span=short_period, adjust=False).mean()
        ema_long = data['last_trade_price'].ewm(span=long_period, adjust=False).mean()

        macd = ema_short - ema_long
        signal = macd.ewm(span=signal_period, adjust=False).mean()

        return macd, signal

    @staticmethod
    def calculate_sma(data, period=30):
        return data['last_trade_price'].rolling(window=period).mean()

    @staticmethod
    def calculate_ema(data, period=30):
        return data['last_trade_price'].ewm(span=period, adjust=False).mean()

class TechnicalAnalysis:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.collection = self.db_manager.get_collection("stock_data")

    def fetch_historical_data(self, stock_code, start_date, end_date):
        start_date = start_date.strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')

        query = {"company_name": stock_code, "date": {"$gte": start_date, "$lte": end_date}}
        cursor = self.collection.find(query)
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
            df[column] = df[column].apply(TechnicalAnalysisUtils.clean_data)

        return df

    def calculate_indicators(self, data):
        data['RSI'] = TechnicalAnalysisUtils.calculate_rsi(data['last_trade_price'])
        data['STOCH_K'], data['STOCH_D'] = TechnicalAnalysisUtils.calculate_stoch(data)
        data['MACD'], data['MACD_SIGNAL'] = TechnicalAnalysisUtils.calculate_macd(data)
        data['SMA'] = TechnicalAnalysisUtils.calculate_sma(data)
        data['EMA'] = TechnicalAnalysisUtils.calculate_ema(data)

        data['RSI_SIGNAL'] = data['RSI'].apply(lambda x: 'BUY' if x < 30 else ('SELL' if x > 70 else 'HOLD'))
        data['STOCH_SIGNAL'] = data['STOCH_K'].apply(lambda x: 'BUY' if x < 20 else ('SELL' if x > 80 else 'HOLD'))
        data['MACD_SIGNAL'] = data['MACD'].apply(lambda x: 'BUY' if x > 0 else 'SELL')
        data['SMA_SIGNAL'] = data.apply(lambda row: 'BUY' if row['last_trade_price'] > row['SMA'] else ('SELL' if row['last_trade_price'] < row['SMA'] else 'HOLD'), axis=1)
        data['EMA_SIGNAL'] = data.apply(lambda row: 'BUY' if row['last_trade_price'] > row['EMA'] else ('SELL' if row['last_trade_price'] < row['EMA'] else 'HOLD'), axis=1)

        return data

    def analyze_stock(self, stock_code, timeperiod=30):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * 2)

            df = self.fetch_historical_data(stock_code, start_date, end_date)
            if df is None:
                return jsonify({"status": "error", "message": f"No data found for stock code {stock_code}"}), 404

            df = self.calculate_indicators(df)

            aggregated_result = {
                "stock_code": stock_code,
                "date_range": f"{df.index.min().strftime('%d.%m.%Y')} - {df.index.max().strftime('%d.%m.%Y')}",
                "last_price": float(df['last_trade_price'].iloc[-1]),
                "SMA_1": float(df['SMA'].iloc[-1]),
                "EMA_1": float(df['EMA'].iloc[-1]),
                "RSI": float(df['RSI'].iloc[-1]),
                "MACD": float(df['MACD'].iloc[-1]),
                "STOCH": float(df['STOCH_K'].iloc[-1]),
                "RSI_SIGNAL": df['RSI_SIGNAL'].iloc[-1],
                "STOCH_SIGNAL": df['STOCH_SIGNAL'].iloc[-1],
                "MACD_SIGNAL": df['MACD_SIGNAL'].iloc[-1],
                "SMA_SIGNAL": df['SMA_SIGNAL'].iloc[-1],
                "EMA_SIGNAL": df['EMA_SIGNAL'].iloc[-1]
            }
            return aggregated_result

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500


def analyze_stock(stock_code, timeperiod=30):
    analyzer = TechnicalAnalysis()
    return analyzer.analyze_stock(stock_code, timeperiod)
