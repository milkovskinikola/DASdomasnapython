import requests, os
from bs4 import BeautifulSoup
from typing import List

class FileManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.file_path = "valid_companies.txt"
        return cls._instance
    
    def read(self) -> List[str]:
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as file:
                return file.read().splitlines()
        return []

    def write(self, data: List[str]):
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write("\n".join(data))

class ParserFactory:
    @staticmethod
    def create_parser(url: str):
        if "mse.mk" in url:
            return MacedonianStockExchangeParser()
        raise ValueError(f"No parser available for URL: {url}")
    
class StockExchangeParser:
    def parse(self, raw_html: str) -> List[str]:
        raise NotImplementedError("Subclasses must implement the `parse` method")
    
class MacedonianStockExchangeParser(StockExchangeParser):
    def parse(self, raw_html: str) -> List[str]:
        soup = BeautifulSoup(raw_html, 'html.parser')
        companies = soup.find_all('option')

        valid_companies = []
        for company in companies:
            company_name = company.text.strip()
            if company_name and company_name.isalpha():
                valid_companies.append(company_name)
        
        return valid_companies

class StockDataFetcher:
    def fetch_and_store(self, url: str) -> List[str]:
        raise NotImplementedError("Subclasses must implement the `fetch_and_store` method.")
    
class ValidCompanyFetcher(StockDataFetcher):
    def fetch_and_store(self, url: str = 'https://www.mse.mk/en/stats/symbolhistory/KMB') -> List[str]:
        try:
            response = requests.get(url)
            response.raise_for_status()

            raw_html = response.text
            parser = ParserFactory.create_parser(url)
            valid_companies = parser.parse(raw_html)

            file_manager = FileManager()
            file_manager.write(valid_companies)
            return valid_companies
        except requests.RequestException as e:
            print(f"Error fetching companies from {url} : {e}")
            return []
        
def fetch_valid():
    file_manager = FileManager()
    company_codes = file_manager.read()
    if company_codes:
        return company_codes
    
    fetcher = ValidCompanyFetcher()
    return fetcher.fetch_and_store()

def main():
    stock_codes = fetch_valid()
    print(f"Stock codes fetched: {stock_codes}")

if __name__ == "__main__":
    main()
