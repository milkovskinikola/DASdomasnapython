import pandas as pd
from transformers import pipeline
import os

def analyze_sentiment_batch(content_list, classifier):
    results = []
    for content in content_list:
        try:
            result = classifier(content, truncation=True, max_length=512)
            results.append(result[0]['label'])
        except Exception as e:
            print(f"Error processing content: {content[:50]}... | Error: {e}")
            continue
    return results

def process_data_in_batches(input_file, classifier_model, output_file, batch_size=32):
    if os.path.exists(output_file):
        print(f"{output_file} already exists. Skipping sentiment analysis...")
        return pd.read_csv(output_file)
    
    data = pd.read_csv(input_file)
    data = data.dropna(subset=['Text_Content'], axis = 0).copy()
    data['Text_Content'] = data['Text_Content'].astype(str)
    data = data[data['Text_Content'].str.strip() != ""]

    classifier = pipeline("sentiment-analysis", model=classifier_model, truncation=True, max_length=512)

    sentiments = []
    for i in range(0, len(data), batch_size):
        batch = data['Text_Content'][i:i+batch_size].tolist()
        sentiments.extend(analyze_sentiment_batch(batch, classifier))

    data['Sentiment'] = sentiments
    data.to_csv(output_file, index=False)
    return data