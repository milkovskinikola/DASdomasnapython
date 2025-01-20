import pandas as pd
from .sentiment import SentimentAnalyzer, SingletonSentimentProcessor
from .visualization import create_chart

class SignalAnalyzer:
    def __init__(self, sentiment_data):
        self.sentiment_data = sentiment_data
    
    def get_signal(self, company_code):
        company_data = self.sentiment_data[self.sentiment_data['Company_Code'] == company_code]

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

        positive_percentage = (positive/total) * 100
        negative_percentage = (negative/total) * 100
        neutral_percentage = (neutral/total) * 100

        signal = (
            "BUY" if positive_percentage > 60 else
            "SELL" if negative_percentage > 60 else
            "HOLD"
        )

        pie_chart_base64 = create_chart("pie", positive_percentage, negative_percentage, neutral_percentage)
        bar_plot_base64 = create_chart("bar", positive, negative, neutral)

        return {
            "company": company_code,
            "positive_percentage": round(positive_percentage, 2),
            "negative_percentage": round(negative_percentage, 2),
            "neutral_percentage": round(neutral_percentage, 2),
            "signal": signal,
            "pie_chart": pie_chart_base64,
            "bar_plot_base64": bar_plot_base64
        }
    
class FundamentalAnalysis:
    def __init__(self, model_name, input_file, output_file):
        self.model_name = model_name
        self.input_file = input_file
        self.output_file = output_file

    def perform_analysis(self, company_code):
        sentiment_analyzer = SentimentAnalyzer(self.model_name)
        processor = SingletonSentimentProcessor(self.input_file, self.output_file)
        sentiment_data = processor.process(sentiment_analyzer)
        signal_analyzer = SignalAnalyzer(sentiment_data)
        return signal_analyzer.get_signal(company_code)
    
def get_fundamental_analysis(company_code):
    input_file = "scraped_vesti.csv"
    output_file = "sentiment_data.csv"
    model_name = "yiyanghkust/finbert-tone"
    analysis = FundamentalAnalysis(model_name, input_file, output_file)
    result = analysis.perform_analysis(company_code)

    return result