import os, csv, requests, html, re, pdfplumber
from io import BytesIO
from datetime import datetime

class CSVManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self, csv_path):
        self.csv_path = csv_path
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Document_ID', 'Publication_date', 'Title', 'Text_Content', 'Company_Name', 'Company_Code'])

    def append_row(self, row):
        with open(self.csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(row)

class ContentExtractorFactory:
    @staticmethod
    def get_content(news_data):
        try:
            content = news_data.get('content', '')
            content = html.unescape(content)
            content = re.sub(r'<[^>]*>', '', content)

            if 'this is automatically generated document'.lower() in content.lower() or \
               "for more information contact".lower() in content.lower():
                return None

            attachments = news_data.get('attachments', [])
            if attachments:
                attachment = attachments[0]
                file_name = attachment.get('fileName', '')
                if file_name.lower().endswith('.pdf'):
                    return PdfContentExtractor().extract_content(attachment)
                
            return content
        except Exception as e:
            print(f"Error extracting content: {e}")
            return None

class PdfContentExtractor:
    def extract_content(self, attachment):
        attachment_url = f"https://api.seinet.com.mk/public/documents/attachment/{attachment.get('attachmentId')}"
        response = requests.get(attachment_url)
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
            with pdfplumber.open(pdf_file) as pdf:
                if pdf.pages:
                    return pdf.pages[0].extract_text()
        return ''
    
class NewsFetcher:
    def __init__(self, api_url):
        self.api_url = api_url
    
    def fetch_news(self, page_num):
        start_date = "2022-01-01T00:00:00"
        end_date = datetime.now().strftime("%Y-%m-%dT23:59:59")
        payload = {
            "issuedId": 0,
            "languageId": 2,
            "channelId": 1,
            "dateFrom": start_date,
            "dateTo": end_date,
            "isPushRequest": False,
            "page": page_num
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(self.api_url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            print(f"Failed to fetch page {page_num}: {response.status_code}")
            return []

def extract_and_process_content(news_data):
    try:
        doc_id = news_data.get('documentId', '')
        company_code = news_data['issuer']['code']
        company_name = news_data['issuer']['localizedTerms'][0]['displayName']
        title = news_data['layout']['description']
        published_date = news_data['publishedDate'].split("T")[0]
        content = ContentExtractorFactory.get_content(news_data)

        if content:
            csv_manager = CSVManager(NEWS_CSV_PATH)
            csv_manager.append_row([doc_id, published_date, title, content, company_name, company_code])
            print(f"Saved document {doc_id} to CSV.")
    except Exception as e:
        print(f"Error processing document {news_data.get('documentId', 'unknown')}: {e}")

def retrieve_all_news():
    news_fetcher = NewsFetcher("https://api.seinet.com.mk/public/documents")
    page_number = 1
    all_news = []

    while True:
        print(f"Fetching data for page {page_number}...")
        page_data = news_fetcher.fetch_news(page_number)
        if not page_data:
            print("No more data to fetch.")
            break
        all_news.extend(page_data)
        page_number += 1
        
    for news_item in all_news:
        extract_and_process_content(news_item)

    print("News data retrieval and processing complete.")

def update_news():
    global NEWS_CSV_PATH
    NEWS_CSV_PATH = "scraped_vesti.csv"
    CSVManager(NEWS_CSV_PATH)
    retrieve_all_news()
