import os, requests, html, re, pdfplumber, csv
from io import BytesIO
from html.parser import HTMLParser
from multiprocessing import Pool
from datetime import datetime

NEWS_CSV_PATH = "scraped_vesti.csv"

def news_csv():
    if not os.path.exists(NEWS_CSV_PATH):
        with open(NEWS_CSV_PATH, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Document_ID', 'Publication_date', 'Title', 'Text_Content', 'Company_Name', 'Company_Code'])
        

def extract_and_process_content(news_data):
    try:
        doc_id = news_data.get('documentId', '')
        content = news_data.get('content', '')
        content = html.unescape(content)
        content = re.sub(r'<[^>]*>', '', content)

        company_code = news_data['issuer']['code']
        company_name = news_data['issuer']['localizedTerms'][0]['displayName']
        title = news_data['layout']['description']
        published_date = news_data['publishedDate'].split("T")[0]

        if 'this is automatically generated document'.lower() in content.lower() or "For more information contact".lower() in content.lower():
            return
        
        attachments = news_data.get('attachments', [])
        if attachments:
            attachment = attachments[0]
            file_name = attachment.get('fileName')
            if file_name.lower().endswith('.pdf'):
                attachment_url = f"https://api.seinet.com.mk/public/documents/attachment/{attachment.get('attachmentId')}"
                response = requests.get(attachment_url)
                if response.status_code == 200:
                    pdf_file = BytesIO(response.content)
                    with pdfplumber.open(pdf_file) as pdf:
                        if pdf.pages:
                            pdf_text = pdf.pages[0].extract_text()
                            content += "\n" + pdf_text
        
        with open(NEWS_CSV_PATH, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([doc_id, published_date, title, content, company_name, company_code])
        
        print(f"Saved document {doc_id} to CSV.")
    except Exception as e:
        print(f"Error processing document {news_data.get('documentId', 'unknown')}: {e}")


def fetch_news_from_api(page_num):
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
    url = "https://api.seinet.com.mk/public/documents"

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        print(f"Failed to fetch page {page_num}: {response.status_code}")
        return []

def retrieve_all_news():
    page_number = 1
    all_news = []
    while True:
        print(f"Fetching data for page {page_number}...")
        page_data = fetch_news_from_api(page_number)
        if not page_data:
            print("No more data to fetch.")
            break
        all_news.extend(page_data)
        page_number += 1

    with Pool(processes=8) as pool:
        pool.map(extract_and_process_content, all_news)

    print("News data retrieval and processing coplete.")

def update_news():
    news_csv()
    retrieve_all_news()