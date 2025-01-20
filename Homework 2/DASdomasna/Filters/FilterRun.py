import asyncio
import time
from Filter1 import fetch_valid
from Filter2 import check_and_get_dates
from Filter3 import fetch_and_store_data_for_stocks

async def measure_scraping_time():
    stock_codes = fetch_valid()

    start_time = time.time()

    print("Fetching last available dates for stocks...")
    stocks_with_dates = check_and_get_dates(stock_codes)

    print("Fetching and storing data for stocks...")
    await fetch_and_store_data_for_stocks(stocks_with_dates)

    end_time = time.time()
    time_taken = end_time - start_time
    print(f"Total time taken for scraping data for all stocks in the last 10 years: {time_taken:.2f} seconds")

def main():
    asyncio.run(measure_scraping_time())

if __name__ == "__main__":
    main()
