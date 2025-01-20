import requests
from bs4 import BeautifulSoup
from typing import List
import os

def fetch_valid():
    file_path = "valid_companies.txt"

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            company_codes = file.read().splitlines()
            if company_codes:
                return company_codes
    return fetch_and_store()

def fetch_and_store(url: str = 'https://www.mse.mk/en/stats/symbolhistory/KMB') -> List[str]:

    try:
        response = requests.get(url)
        response.raise_for_status()

        raw_html = response.text
        soup = BeautifulSoup(raw_html, 'html.parser')

        companies = soup.find_all('option')

        valid_companies = []
        for company in companies:
            company_name = company.text.strip()
            if company_name and company_name.isalpha():
                valid_companies.append(company_name)
        with open("valid_companies.txt", 'w', encoding="utf-8") as file:
            file.write("\n".join(valid_companies))

        return valid_companies

    except requests.RequestException as e:
        print(f"Error fetching companies from {url}: {e}")
        return []

def main():
    stock_codes = fetch_valid()
    print(f"Stock codes fetched: {stock_codes}")

if __name__ == "__main__":
    main()
