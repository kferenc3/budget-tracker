from unittest import mock

import requests
from src.web_data import fetch_exchange_rates

@mock.patch("src.web_data.requests.get")
@mock.patch("src.web_data.os.getenv", return_value="dummy_app_id")
def test_fetch_exchange_rates_success(mock_getenv, mock_get):
    test_values = {"rates": {
            "EUR": 0.92,
            "GBP": 0.78,
            "HUF": 360.0,
            "USD": 1.0
        }
    }
    mock_response = mock.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = test_values
    mock_get.return_value = mock_response

    symbols = ['EUR', 'GBP', 'HUF', 'USD']
    result = fetch_exchange_rates(symbols)
    print(result)
    assert isinstance(result, list)
    assert any(r['from_currency'] == 'USD' for r in result)
    assert any(r['from_currency'] == 'EUR' for r in result)
    assert any(r['from_currency'] == 'GBP' for r in result)
    for r in result:
        if r['from_currency'] == r['to_currency']:
            assert r['rate'] == float(1)
        else:
            assert r['rate'] == test_values['rates'][r['to_currency']] * (1/test_values['rates'][r['from_currency']])
        assert r['to_currency'] in symbols
        assert isinstance(r['rate'], float)
        assert 'date' in r

@mock.patch("src.web_data.requests.get")
@mock.patch("src.web_data.os.getenv", return_value="dummy_app_id")
def test_fetch_exchange_rates_missing_symbol(mock_getenv, mock_get):
    mock_response = mock.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "rates": {
            "EUR": 0.92,
            "HUF": 360.0,
            "USD": 1.0
        }
    }
    mock_get.return_value = mock_response

    symbols = ['EUR', 'GBP', 'HUF', 'USD']
    result = fetch_exchange_rates(symbols)
    # GBP is missing, so it should not be in the result
    assert all(r['from_currency'] != 'GBP' for r in result)

@mock.patch("src.web_data.requests.get", side_effect=Exception("Network error"))
@mock.patch("src.web_data.os.getenv", return_value="dummy_app_id")
def test_fetch_exchange_rates_request_network_exception(mock_getenv, mock_get):
    symbols = ['EUR', 'GBP', 'HUF', 'USD']
    result = fetch_exchange_rates(symbols)
    assert result == [{}]

@mock.patch("src.web_data.requests.get", side_effect=requests.RequestException("API error"))
@mock.patch("src.web_data.os.getenv", return_value="dummy_app_id")
def test_fetch_exchange_rates_request_exception(mock_getenv, mock_get):
    symbols = ['EUR', 'GBP', 'HUF', 'USD']
    result = fetch_exchange_rates(symbols)
    assert result == [{}]

@mock.patch("src.web_data.requests.get")
@mock.patch("src.web_data.os.getenv", return_value="dummy_app_id")
def test_fetch_exchange_rates_empty_symbols(mock_getenv, mock_get):
    mock_response = mock.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "rates": {
            "EUR": 0.92,
            "GBP": 0.78,
            "HUF": 360.0,
            "USD": 1.0
        }
    }
    mock_get.return_value = mock_response

    result = fetch_exchange_rates([])
    assert result == []