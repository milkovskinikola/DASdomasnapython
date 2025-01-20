import pandas as pd
from .sentiment import process_data_in_batches
from .visualization import create_pie_chart, create_bar_plot

def get_signal(sentiment_data, company_code):
    company_data = sentiment_data[sentiment_data['Company_Code'] == company_code]

    if company_data.empty:
        return {"error": f"No data found for company code: {company_code}"}

    sentiments = company_data.get('Sentiment')

    if sentiments is None or not isinstance(sentiments, pd.Series):
        return {"error": f"Invalid 'Sentiment' data for company code: {company_code}"}

    counts = sentiments.value_counts()
    positive = counts.get("Positive", 0)
    negative = counts.get("Negative", 0)
    neutral = counts.get("Neutral", 0)
    total = len(sentiments)
    if total == 0:
        return {"error": f"No sentiment data available for company code: {company_code}"}
    positive_percentage = (positive / total) * 100
    negative_percentage = (negative / total) * 100
    neutral_percentage = (neutral / total) * 100

    signal = (
        "BUY" if positive_percentage > 60 else
        "SELL" if negative_percentage > 60 else
        "HOLD"
    )
    pie_chart_base64 = create_pie_chart(positive_percentage, negative_percentage, neutral_percentage)
    print("SREDINA")
    bar_plot_base64 = create_bar_plot(positive, negative, neutral)
    print("HERE5")

    return {
        "company": company_code,
        "positive_percentage": round(positive_percentage, 2),
        "negative_percentage": round(negative_percentage, 2),
        "neutral_percentage": round(neutral_percentage, 2),
        "signal": signal,
        "pie_chart": pie_chart_base64,
        "bar_plot_base64": bar_plot_base64
    }

def get_fundamental_analysis(company_code):
    news_data = "scraped_vesti.csv"
    news_sentiment_data = "sentiment_data.csv"
    classifier_model = "yiyanghkust/finbert-tone"

    sentiment_data = process_data_in_batches(news_data, classifier_model, news_sentiment_data)
    result  = get_signal(sentiment_data, company_code)

    return result