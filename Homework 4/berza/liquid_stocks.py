import requests
from bs4 import BeautifulSoup

class RequestManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.session = requests.Session()
        return cls._instance

    def get(self, url):
        return self.session.get(url)

class DataExtractorFactory:
    @staticmethod
    def get_data(url):
        try:
            response = RequestManager().get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('div', {'id': 'topSymbolValueTopSymbols'}).find('table')

            if not table:
                raise ValueError("The required table could not be found on the page.")

            return TableDataExtractor().extract_data(table)
        except Exception as e:
            print(f"Error extracting data: {e}")
            return {"error": "Failed to retrieve or process data from the MSE website."}


class TableDataExtractor:
    def extract_data(self, table):
        try:
            headers = [th.text.strip() for th in table.find_all('th')]
            data = []
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if cells:
                    data.append({
                        "Company_Code": cells[0].text.strip(),
                        "average_price": cells[1].text.strip(),
                        "percent_change": cells[2].text.strip(),
                        "turnover": cells[3].text.strip(),
                    })
            return data
        except Exception as e:
            print(f"Error parsing table data: {e}")
            return {"error": "Failed to parse table data."}

def most_liquid_stocks():
    url = "https://www.mse.mk/mk"
    return DataExtractorFactory.get_data(url)
