import requests
from bs4 import BeautifulSoup

def most_liquid_stocks():
    url = "https://www.mse.mk/mk"
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('div', {'id': 'topSymbolValueTopSymbols'}).find('table')

        headers = [th.text.strip() for th in table.find_all('th')]

        data = []
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if cells:
                symbol = cells[0].text.strip()
                data.append({
                    "Company_Code": symbol,
                    "average_price": cells[1].text.strip(),
                    "percent_change": cells[2].text.strip(),
                    "turnover": cells[3].text.strip(),
                })
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return {"error": "Failed to retrieve data from the MSE website."}