from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import List

class MongoDBConnection:
    _instance = None

    def __new__(cls, db_url: str = "mongodb://mongo:27017/"):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.client = MongoClient(db_url)
        return cls._instance

    def get_database(self, db_name: str):
        return self.client[db_name]


class DateParser:
    def parse(self, date_str: str) -> datetime:
        raise NotImplementedError("Subclasses must implement the `parse` method.")


class DefaultDateParser(DateParser):
    def parse(self, date_str: str) -> datetime:
        return datetime.strptime(date_str.strip(), '%d.%m.%Y')


class DateParserFactory:
    @staticmethod
    def create_parser() -> DateParser:
        return DefaultDateParser()


class LastDateFetcher:
    def __init__(self, db, collection_name: str = "stock_data"):
        self.collection = db[collection_name]
        self.default_date = datetime.now() - timedelta(days=365 * 10)

    def get_last_dates(self, stock_codes: List[str]) -> List[dict]:
        raise NotImplementedError("Subclasses must implement the `get_last_dates` method.")


class StockDateFetcher(LastDateFetcher):
    def get_last_dates(self, stock_codes: List[str]) -> List[dict]:
        pipeline = [
            {"$match": {"stock_code": {"$in": stock_codes}}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$stock_code",
                "last_date": {"$first": "$date"}
            }}
        ]
        results = list(self.collection.aggregate(pipeline))
        stock_dates = {result["_id"]: result["last_date"] for result in results}

        parser = DateParserFactory.create_parser()

        date_for_stocks = []
        for stock_code in stock_codes:
            last_date = stock_dates.get(stock_code)
            if last_date:
                last_date_parsed = parser.parse(last_date)
            else:
                last_date_parsed = self.default_date
            date_for_stocks.append({
                "stock_code": stock_code,
                "last_date": last_date_parsed.strftime('%Y-%m-%d')
            })
        return date_for_stocks


def check_and_get_dates(stock_codes: List[str]) -> List[dict]:
    connection = MongoDBConnection()
    db = connection.get_database("stock_data_db")
    fetcher = StockDateFetcher(db)
    return fetcher.get_last_dates(stock_codes)


if __name__ == "__main__":
    stock_codes = ["KMB", "ALK"]
    stock_dates = check_and_get_dates(stock_codes)
    print(stock_dates)
