import requests
import dotenv
import os

from datetime import datetime
dotenv.load_dotenv()

def fetch_exchange_rates(symbols: list) -> list[dict]:
    """Fetch the latest currency exchange rates from an open exchange rates' api.
    The api always gives results with USD base currency."""
    url_base = "https://openexchangerates.org/api/"  # Example API endpoint
    headers = {"accept": "application/json"}
    app_id = os.getenv("APP_ID")
    today = datetime.now().date()
    try:
        response = requests.get(url_base + f"latest.json?app_id={app_id}&symbols={','.join(symbols)}", headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
    except requests.RequestException as e:
        print(f"Error fetching exchange rates: {e}")
        return [{}]
    except Exception as e:
        print(f"Unexpected error: {e}")
        return [{}]
    result = []
    for from_curr in symbols:
        if from_curr not in data['rates']:
            print(f"Symbol {from_curr} not found in the response.")
            continue
        for to_curr in symbols:
            if to_curr not in data['rates']:
                continue
            if from_curr == 'USD':
                result.append({'from_currency': from_curr, 'to_currency': to_curr, 'rate': data['rates'][to_curr], 'date': today})
            else:
                result.append({'from_currency': from_curr, 'to_currency': to_curr, 'rate': data['rates'][to_curr] * (1/data['rates'][from_curr]), 'date': today})

    return result

if __name__ == "__main__":
    symbols = ["EUR", "GBP", "HUF", "USD"]
    rates = fetch_exchange_rates(symbols)
    print(rates)