import asyncio
import aiohttp
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from pymongo import MongoClient
from typing import List
from aiohttp import TCPConnector


# Singleton Pattern for MongoDB Connection
class MongoDBConnection:
    _instance = None

    def __new__(cls, mongo_uri="mongodb://mongo:27017/"):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.client = MongoClient(mongo_uri)
        return cls._instance

    def get_database(self, db_name: str):
        return self.client[db_name]


# Strategy Pattern for Price Formatting
class PriceFormatter:
    def format(self, price_str: str) -> float:
        raise NotImplementedError("Subclasses must implement the `format` method.")


class DefaultPriceFormatter(PriceFormatter):
    def format(self, price_str: str) -> float:
        if not price_str:
            return 0.0

        # Replace commas with periods and remove thousands separators
        price_str = price_str.replace(",", "").replace(".", "", price_str.count(".") - 1)  # Keep only one dot
        try:
            return float(price_str)
        except ValueError:
            return 0.0  # Return 0.0 if parsing fails


# Factory Pattern for Price Formatter
class PriceFormatterFactory:
    @staticmethod
    def create_formatter() -> PriceFormatter:
        return DefaultPriceFormatter()


# Template Method Pattern for Data Fetching and Storing
class DataFetcher:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.price_formatter = PriceFormatterFactory.create_formatter()

    async def fetch_data(self, session, company_name: str, start_date: str, end_date: str) -> List[dict]:
        raise NotImplementedError("Subclasses must implement the `fetch_data` method.")

    def process_row(self, row, company_name: str):
        raise NotImplementedError("Subclasses must implement the `process_row` method.")


class StockDataFetcher(DataFetcher):
    def __init__(self, base_url: str):
        super().__init__(base_url)

    async def fetch_data(self, session, company_name: str, start_date: str, end_date: str, max_retries=5) -> List[dict]:
        url = f"{self.base_url}/{company_name}"
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        rows = []
        current_start = start_date

        while current_start < end_date:
            current_end = min(current_start + timedelta(days=365), end_date)
            params = {
                "FromDate": current_start.strftime('%m/%d/%Y'),
                "ToDate": current_end.strftime('%m/%d/%Y')
            }

            retries = 0
            while retries < max_retries:
                try:
                    async with session.get(url, params=params) as response:
                        if response.status == 503:
                            retries += 1
                            wait_time = 2
                            print(f"503 error, retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue
                        response.raise_for_status()
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        table_body = soup.find('tbody')
                        if table_body:
                            rows_in_table = table_body.find_all('tr')
                            for row in rows_in_table:
                                row_data = self.process_row(row, company_name)
                                if row_data:
                                    rows.append(row_data)
                        break
                except aiohttp.ClientResponseError:
                    if retries == max_retries - 1:
                        print(f"Failed to fetch data for {company_name} after {max_retries} attempts.")
                        return []
                    retries += 1
                    wait_time = 2
                    print(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
            current_start = current_end + timedelta(days=1)

        return rows

    def process_row(self, row, company_name: str):
        cells = row.find_all('td')
        if not cells:
            return None

        volume = int(cells[6].text.strip().replace(",", "") or 0)
        if volume == 0:
            return None

        return {
            "company_name": company_name,
            "date": datetime.strptime(cells[0].text.strip(), "%m/%d/%Y").strftime("%Y-%m-%d"),
            "last_trade_price": self.price_formatter.format(cells[1].text.strip()),
            "max_price": self.price_formatter.format(cells[2].text.strip()),
            "min_price": self.price_formatter.format(cells[3].text.strip()),
            "avg_price": self.price_formatter.format(cells[4].text.strip()),
            "percent_change": self.price_formatter.format(cells[5].text.strip()),
            "volume": volume,
            "turnover": self.price_formatter.format(cells[7].text.strip()),
            "total_turnover": self.price_formatter.format(cells[8].text.strip())
        }


# Asynchronous Processing and Storage Manager
class DataProcessor:
    def __init__(self, fetcher: DataFetcher, mongo_collection):
        self.fetcher = fetcher
        self.collection = mongo_collection

    async def process_and_store(self, companies_with_dates: List[dict]):
        connector = TCPConnector(limit_per_host=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self.fetcher.fetch_data(session, company["stock_code"], company["last_date"],
                                        datetime.now().strftime('%Y-%m-%d'))
                for company in companies_with_dates
            ]
            results = await asyncio.gather(*tasks)
            for result in results:
                if result:
                    self.collection.insert_many(result)
                    print(f"Inserted {len(result)} records into MongoDB.")


# Main Functionality
async def fetch_and_store_data_for_stocks(companies_with_dates: List[dict]):
    connection = MongoDBConnection()
    db = connection.get_database("stocks_db")
    collection = db["stock_data"]

    fetcher = StockDataFetcher("https://www.mse.mk/en/stats/symbolhistory")
    processor = DataProcessor(fetcher, collection)
    await processor.process_and_store(companies_with_dates)
