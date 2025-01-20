import os
import pandas as pd
import numpy as np
from pymongo import MongoClient
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt
from datetime import datetime


class LSTMFactory:
    def __init__(self):
        self.client = MongoClient("mongodb://mongo:27017/")
        self.db = self.client["stocks_db"]
        self.collection = self.db["stock_data"]

    def fetch_stock_data(self, stock_code):
        cursor = self.collection.find(
            {'company_name': stock_code},
            {'_id': 0, 'date': 1, 'last_trade_price': 1, 'min_price': 1, 'max_price': 1, 'volume': 1}
        )
        data = pd.DataFrame(list(cursor))

        def clean_data(value):
            if isinstance(value, str):
                value = value.replace(',', '.')
                if value.count('.') > 1:
                    value = value.replace('.', '', value.count('.') - 1)
                try:
                    return float(value)
                except ValueError:
                    return np.nan
            return value

        data['last_trade_price'] = data['last_trade_price'].apply(clean_data)
        data['min_price'] = data['min_price'].apply(clean_data)
        data['max_price'] = data['max_price'].apply(clean_data)
        data['volume'] = data['volume'].apply(clean_data)

        data['date'] = pd.to_datetime(data['date'], dayfirst=False)
        data.set_index('date', inplace=True)
        data.sort_index(ascending=True, inplace=True)

        return data

    def preprocess_data(self, stock_data):
        stock_data = stock_data[['last_trade_price']]
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(stock_data)

        train_size = int(len(scaled_data) * 0.7)
        train_data, test_data = scaled_data[:train_size], scaled_data[train_size:]

        def create_dataset(dataset, time_step=60):
            x, y = [], []
            for i in range(len(dataset) - time_step - 1):
                x.append(dataset[i:(i + time_step), 0])
                y.append(dataset[i + time_step, 0])
            return np.array(x), np.array(y)

        time_step = 60
        x_train, y_train = create_dataset(train_data, time_step)
        x_test, y_test = create_dataset(test_data, time_step)

        x_train = x_train.reshape(x_train.shape[0], x_train.shape[1], 1)
        x_test = x_test.reshape(x_test.shape[0], x_test.shape[1], 1)

        return x_train, y_train, x_test, y_test, scaler

    def build_lstm_model(self, input_shape):
        model = Sequential()
        model.add(LSTM(units=50, return_sequences=True, input_shape=input_shape))
        model.add(LSTM(units=50, return_sequences=False))
        model.add(Dense(units=1))
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
        return model

    def train_and_save_lstm_model(self, stock_code):
        stock_data = self.fetch_stock_data(stock_code)
        x_train, y_train, x_test, y_test, scaler = self.preprocess_data(stock_data)

        model = self.build_lstm_model((x_train.shape[1], 1))
        model.fit(x_train, y_train, epochs=10, batch_size=32)

        if not os.path.exists('models'):
            os.makedirs('models')

        model.save(f'models/{stock_code}_lstm_model.h5')
        self.update_last_updated(stock_code)

    def update_last_updated(self, stock_code):
        last_updated = datetime.now().strftime('%d.%m.%Y')
        with open(f'models/{stock_code}_last_updated.txt', 'w') as f:
            f.write(last_updated)

    def generate_signal(self, current_price, predicted_price):
        if predicted_price > current_price * 1.02:
            return "Buy"
        elif predicted_price < current_price * 0.98:
            return "Sell"
        else:
            return "Hold"

    def generate_prediction_plot(self, y_test, predicted_price, stock_code):
        plt.figure(figsize=(10, 6))
        plt.plot(y_test, label="Actual Price", color="blue")
        plt.plot(predicted_price, label="Predicted Price", color="red")
        plt.title(f"Stock Prediction for {stock_code}")
        plt.xlabel("Time")
        plt.ylabel("Stock Price")
        plt.legend()
        plot_path = f'static/plot/{stock_code}_prediction_plot.png'
        plt.savefig(plot_path)
        plt.close()

    def predict_stock_price(self, stock_code):
        try:
            model_path = f'models/{stock_code}_lstm_model.h5'

            if not os.path.exists(model_path):
                self.train_and_save_lstm_model(stock_code)
                message = f"Model for {stock_code} was not found and has been created."
            else:
                message = f"Model for {stock_code} was found."

            stock_data = self.fetch_stock_data(stock_code)
            x_train, y_train, x_test, y_test, scaler = self.preprocess_data(stock_data)

            model = load_model(model_path)

            predicted_price = model.predict(x_test)
            predicted_price = scaler.inverse_transform(predicted_price)
            y_test = scaler.inverse_transform(y_test.reshape(-1, 1))

            self.generate_prediction_plot(y_test, predicted_price, stock_code)

            current_price = stock_data["last_trade_price"].iloc[-1]
            signal = self.generate_signal(current_price, predicted_price[-1][0])

            predicted_price_last = float(predicted_price[-1][0])

            last_updated_path = f'models/{stock_code}_last_updated.txt'
            if os.path.exists(last_updated_path):
                with open(last_updated_path, 'r') as f:
                    last_updated = f.read().strip()
            else:
                last_updated = "N/A"

            return {
                "message": message,
                "predicted_price": predicted_price_last,
                "signal": signal,
                "last_updated": last_updated
            }
        except Exception as e:
            return {"error": str(e)}