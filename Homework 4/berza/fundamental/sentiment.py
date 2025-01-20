import os
import pandas as pd
from transformers import pipeline
from typing import List

class SentimentAnalyzer:

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.classifier = self._get_classifier()

    def _get_classifier(self):
        return pipeline("sentiment-analysis", model=self.model_name, truncation=True, max_length=512)


    def analyze_batch(self, content_list: List[str]) -> List[str]:
        results = []
        for content in content_list:
            try:
                result = self.classifier(content, truncation=True, max_length=512)
                results.append(result[0]['label'])
            except Exception as e:
                print(f"Error processing content: {content[:50]}... | Error: {e}")
                results.append("Error")
        return results
    
class SentimentProcessor:
    def __init__(self, input_file: str, output_file: str, batch_size: int=32):
        self.input_file = input_file
        self.output_file = output_file
        self.batch_size = batch_size
    
    def _load_data(self) -> pd.DataFrame:
        data = pd.read_csv(self.input_file)
        data = data.dropna(subset=['Text_Content']).copy()
        data['Text_Content'] = data['Text_Content'].astype(str).str.strip()
        return data[data['Text_Content'] != ""]

    def _save_results(self, data: pd.DataFrame):
        data.to_csv(self.output_file, index=False)
    
    def process(self, analyzer: SentimentAnalyzer) -> pd.DataFrame:
        if os.path.exists(self.output_file):
            print(f"{self.output_file} already exists. Skipping sentiment analysis...")
            return pd.read_csv(self.output_file)
        
        data = self._load_data()
        sentiments = []

        for i in range(0, len(data), self.batch_size):
            batch = data['Text_Content'][i:i+self.batch_size].tolist()
            sentiments.extend(analyzer.analyze_batch(batch))

        data['Sentiment'] = sentiments
        self._save_results(data)
        return data
    
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class SingletonSentimentProcessor(SentimentProcessor, metaclass=SingletonMeta):
    pass

def main():
    input_file = "input.csv"
    output_file = "output.csv"
    model_name = "distilbert-base-uncased-finetuned-sst-2-english"

    analyzer = SentimentAnalyzer(model_name)

    processor = SingletonSentimentProcessor(input_file, output_file)
    result_data = processor.process(analyzer)

    print("Sentiment analysis complete.")
    print(result_data.head())

if __name__ == "__main__":
    main()