import asyncio
import aiohttp
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from pymongo import MongoClient
from typing import List
from aiohttp import TCPConnector


class FetchDataFilter:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="stocks_db", collection_name="stock_data"):
        self.base_url = 'https://www.mse.mk/en/stats/symbolhistory'
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

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
                                cells = row.find_all('td')
                                if cells:
                                    volume = int(cells[6].text.strip().replace(",", "") or 0)
                                    if volume == 0:
                                        continue
                                    rows.append({
                                        "company_name": company_name,
                                        "date": datetime.strptime(cells[0].text.strip(), "%m/%d/%Y").strftime("%Y-%m-%d"),
                                        "last_trade_price": self.format_price(cells[1].text.strip()),  # Store as float
                                        "max_price": self.format_price(cells[2].text.strip()),  # Store as float
                                        "min_price": self.format_price(cells[3].text.strip()),  # Store as float
                                        "avg_price": self.format_price(cells[4].text.strip()),  # Store as float
                                        "percent_change": self.format_price(cells[5].text.strip()),  # Store as float
                                        "volume": volume,
                                        "turnover": self.format_price(cells[7].text.strip()),  # Store as float
                                        "total_turnover": self.format_price(cells[8].text.strip())  # Store as float
                                    })
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

    def format_price(self, price_str: str) -> float:
        """Format the price as a float for consistency."""
        if not price_str:
            return 0.0

        # Replace commas with periods and remove thousands separators
        price_str = price_str.replace(",", "").replace(".", "", price_str.count(".") - 1)  # Keep only one dot
        try:
            return float(price_str)
        except ValueError:
            return 0.0  # Return 0.0 if parsing fails

    async def process(self, companies_with_dates: List[dict]) -> List[List[dict]]:
        connector = TCPConnector(limit_per_host=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self.fetch_data(session, company_info["stock_code"], company_info["last_date"],
                                datetime.now().strftime('%Y-%m-%d'))
                for company_info in companies_with_dates
            ]
            results = await asyncio.gather(*tasks)
            return list(results)

    async def store_in_mongodb(self, stock_data: List[dict]):
        if stock_data:
            self.collection.insert_many(stock_data)
            print(f"Inserted {len(stock_data)} records into MongoDB.")
        else:
            print("No data to insert into MongoDB.")

    async def fetch_and_store_data_for_stocks(self, companies_with_dates: List[dict]):
        results = await self.process(companies_with_dates)
        for result in results:
            await self.store_in_mongodb(result)

async def fetch_and_store_data_for_stocks(companies_with_dates: List[dict]):
    filter3 = FetchDataFilter()
    await filter3.fetch_and_store_data_for_stocks(companies_with_dates)
