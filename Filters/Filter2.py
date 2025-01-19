from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import List

class LastDateChecker:
    def __init__(self, db_url: str = "mongodb://localhost:27017/", db_name: str="stock_data_db", collection_name: str = "stock_data"):
        self.client = MongoClient(db_url)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.default_date = datetime.now() - timedelta(days=365*10)

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

        date_for_stocks = []
        for stock_code in stock_codes:
            last_date = stock_dates.get(stock_code)
            if last_date:
                last_date_parsed = datetime.strptime(last_date.strip(), '%d.%m.%Y')
            else:
                last_date_parsed = self.default_date
            date_for_stocks.append({
                "stock_code": stock_code,
                "last_date": last_date_parsed.strftime('%Y-%m-%d')
            })
        return date_for_stocks

def check_and_get_dates(stock_codes: List[str]) -> List[dict]:
    checker = LastDateChecker()
    date_for_stocks = checker.get_last_dates(stock_codes)
    return date_for_stocks