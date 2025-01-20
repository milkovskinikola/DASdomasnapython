import pandas as pd
import numpy as np
import base64
import plotly.graph_objs as go
from flask import Flask, render_template, jsonify, request, flash
from Filters.Filter1 import fetch_valid
from auth import auth_router
from Predictors.LSTM import LSTMFactory
from pymongo import MongoClient
from Predictors.technical_analysis_api import analyze_stock
from collect_news import update_news
from liquid_stocks import most_liquid_stocks
from fundamental.fundamental_analysis import get_fundamental_analysis

# Flask application setup
app = Flask(__name__, static_folder="static")
app.config['SECRET_KEY'] = 'DAS-DAS-DAS'
app.config['STATIC_FOLDER'] = 'static'
app.config['TEMPLATES_FOLDER'] = 'templates'

# MongoDB Client Singleton
class MongoDBClient:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.client = MongoClient("mongodb://mongo:27017/")
            cls._instance.db = cls._instance.client["stocks_db"]
        return cls._instance

mongo_client = MongoDBClient()
db = mongo_client.db
collection = db["stock_data"]

# Register authentication routes
app.register_blueprint(auth_router, url_prefix="/auth")

# Graph Factory for visualizations
class GraphFactory:
    @staticmethod
    def create_graph(graph_type, df, stock_code):
        if graph_type == "trading":
            trace = go.Scatter(x=df['date'], y=df['last_trade_price'], mode='lines+markers', 
                        name='Close Price', marker=dict(color='blue', size=8))
            trace_min = go.Scatter(x=df['date'], y=df['min_price'], mode='markers', 
                                name='Min Price', marker=dict(color='red', size=6))
            trace_max = go.Scatter(x=df['date'], y=df['max_price'], mode='markers', 
                                name='Max Price', marker=dict(color='green', size=6))
            trace_qty = go.Bar(x=df['date'], y=df['volume'], name='volume', 
                            marker=dict(color='gray', opacity=0.3), yaxis='y2')

            layout = go.Layout(
                title={
                    'text': f"Trading Data for {stock_code}",
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis={
                    'rangeslider': {'visible': True},
                    'title': 'Date',
                    'type': 'date',
                    'tickformat': '%d %b, %Y'
                },
                yaxis={'title': 'Price', 'type': 'log'},
                yaxis2=dict(title='volume', overlaying='y', side='right'),
                template='plotly_dark',
                height=600,
                margin=dict(t=60, b=40, l=40, r=40),
                updatemenus=[
                    {
                        'buttons': [
                            {'label': 'Last Week',
                            'method': 'relayout',
                            'args': [{'xaxis.range': [df['date'].max() - pd.Timedelta(days=7), df['date'].max()]}]},
                            {'label': 'Last Month',
                            'method': 'relayout',
                            'args': [{'xaxis.range': [df['date'].max() - pd.Timedelta(days=30), df['date'].max()]}]},
                            {'label': 'Last Year',
                            'method': 'relayout',
                            'args': [{'xaxis.range': [df['date'].max() - pd.Timedelta(days=365), df['date'].max()]}]},
                            {'label': 'Last 5 Years',
                            'method': 'relayout',
                            'args': [{'xaxis.range': [df['date'].max() - pd.Timedelta(days=1825), df['date'].max()]}]},
                            {'label': 'All Data',
                            'method': 'relayout',
                            'args': [{'xaxis.range': [df['date'].min(), df['date'].max()]}]},
                        ],
                        'direction': 'down',
                        'showactive': True,
                        'x': 0.95,
                        'y': 1.15,
                        'xanchor': 'right',
                        'yanchor': 'top'
                    }
                ]
            )

            figure = go.Figure(data=[trace, trace_min, trace_max, trace_qty], layout=layout)
            return figure.to_html(full_html=False)
        else:
            raise ValueError(f"Graph type '{graph_type}' not supported.")

# Data cleaning utility
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

# API Routes

class PredictionHandler:
    @staticmethod
    def prediction_plot(stock_code):
        plot_path = f"static/plot/{stock_code}_prediction_plot.png"

        try:
            with open(plot_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            return jsonify({
                "stock_code": stock_code,
                "image": encoded_image
            })
        except FileNotFoundError:
            return jsonify({"error": "Plot not found"}), 404

    @staticmethod
    def prediction_lstm(stock_code):
        try:
            lstm_factory = LSTMFactory()
            lstm_data = lstm_factory.predict_stock_price(stock_code)
            return jsonify({
                'predicted_price': lstm_data.get('predicted_price'),
                'signal': lstm_data.get('signal'),
                'last_updated': lstm_data.get('last_updated')
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

@app.route("/", methods=["GET"])
def read_root():
    return render_template("login.html")

@app.route("/filter1", methods=["GET"])
def filter1():
    valid_stocks = fetch_valid()
    return jsonify({"result": valid_stocks})

@app.route('/index', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/prediction_plot/<stock_code>', methods=['GET'])
def prediction_plot(stock_code):
    return PredictionHandler.prediction_plot(stock_code)

@app.route('/lstm/prediction/<stock_code>', methods=['GET'])
def prediction_lstm(stock_code):
    return PredictionHandler.prediction_lstm(stock_code)

@app.route('/most_liquid', methods=['GET'])
def most_liquid():
   data = most_liquid_stocks()
   return jsonify(data)

@app.route('/update_news', methods=['POST'])
def update_news_api():
    try:
        update_news()
        return {"status": "success", "message": "News data gathered"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/generate_sentiment/<company_code>', methods=['GET'])
def sentiment(company_code):
    print(company_code)
    try:
        result = get_fundamental_analysis(company_code)
        print("HERE")
        if 'error' in result:
            return jsonify(result), 404
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/company_info/<stock_code>', methods=['GET'])
def company_info(stock_code):
    trading_data = list(collection.find({"company_name": stock_code}))
    if not trading_data:
        flash("Company not found", "error")
        return render_template("index.html")
    
    df = pd.DataFrame(trading_data)
    df['date'] = pd.to_datetime(df['date'], dayfirst=False)
    df['last_trade_price'] = df['last_trade_price'].apply(clean_data)
    df['min_price'] = df['min_price'].apply(clean_data)
    df['max_price'] = df['max_price'].apply(clean_data)
    df['volume'] = df['volume'].apply(clean_data)
    
    graph_html = GraphFactory.create_graph("trading", df, stock_code)

    try:
        analysis_data = analyze_stock(stock_code)
    except Exception as e:
        analysis_data = {}

    return render_template(
        'company_info.html',
        company={'name': stock_code},
        graph_html=graph_html,
        analysis_data=analysis_data,
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
