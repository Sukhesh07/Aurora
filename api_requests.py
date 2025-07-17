import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

import requests
from ratelimit import limits, sleep_and_retry


# --- Configuration ---

class ApiConfig:
    # Rate limiting
    NASDAQ_CALLS = 30
    NASDAQ_PERIOD = 60
    # Increased FMP limits for the more intensive data fetching
    FMP_CALLS = 15
    FMP_PERIOD = 4

    # Base URLs
    NASDAQ_BASE_URL = 'https://api.nasdaq.com/api'
    FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'


# --- Custom Exception ---

class APIError(Exception):
    """Custom exception for API-related errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


# --- Base Client ---

class BaseApiClient:
    """A base class for API clients to handle requests and errors."""

    def __init__(self):
        self.session = requests.Session()

    def _request(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Any:
        """A wrapper around requests.get with comprehensive debugging and error handling."""
        print("\n--- [DEBUG] Making API Request ---")
        print(f"URL: {url}")
        if params:
            masked_params = {k: ('**********' if k == 'apikey' else v) for k, v in params.items()}
            print(f"PARAMS: {masked_params}")

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            print(f"[DEBUG] Response Status Code: {response.status_code}")
            print(f"[DEBUG] Raw Response Text: {response.text}")
            response.raise_for_status()

            if not response.text:
                print("[DEBUG] Response text is empty.")
                return None

            data = response.json()
            if not data:
                print(f"[DEBUG] Parsed JSON is empty or None. Response was: {response.text}")
                return None

            print("[DEBUG] Successfully parsed JSON data.")
            return data

        except requests.exceptions.HTTPError as http_err:
            raise APIError(status_code=http_err.response.status_code, message=str(http_err)) from http_err
        except requests.exceptions.JSONDecodeError:
            raise APIError(status_code=response.status_code,
                           message=f"Failed to decode JSON. Response was: {response.text}")
        except requests.exceptions.RequestException as req_err:
            raise APIError(status_code=503, message=f"Network error: {req_err}") from req_err
        finally:
            print("--- [DEBUG] End Request ---\n")


# --- Specific API Clients ---

class NasdaqApiClient(BaseApiClient):
    """Client for interacting with the NASDAQ API."""

    def __init__(self):
        super().__init__()
        self.base_url = ApiConfig.NASDAQ_BASE_URL
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com",
            "User-Agent": "Mozilla/5.0"
        })

    @sleep_and_retry
    @limits(calls=ApiConfig.NASDAQ_CALLS, period=ApiConfig.NASDAQ_PERIOD)
    def get_earnings(self, date: str) -> Optional[Dict[str, Any]]:
        """Get earnings calendar data from NASDAQ for a specific date."""
        print(f"Fetching NASDAQ earnings for {date}")
        url = f"{self.base_url}/calendar/earnings"
        data = self._request(url, params={"date": date})

        if not data or 'data' not in data or 'rows' not in data['data']:
            raise APIError(status_code=200, message="Invalid data format received from NASDAQ API")

        return data


class FmpApiClient(BaseApiClient):
    """Client for interacting with the Financial Modeling Prep API."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or os.getenv('FINANCIAL_API_KEY')
        if not self.api_key:
            raise ValueError("FMP API key not provided or set in FINANCIAL_API_KEY environment variable.")
        self.base_url = ApiConfig.FMP_BASE_URL
        self.params = {'apikey': self.api_key}

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_earnings_data(self, symbol: str, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Get historical earnings data for a specific symbol."""
        print(f"Fetching FMP earnings for {symbol}")
        url = f"{self.base_url}/earnings-surprises/{symbol}"

        request_params = self.params.copy()
        if limit:
            request_params['limit'] = limit

        return self._request(url, params=request_params)

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_historical_price_full(self, symbol: str, limit: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get full historical daily price data for a symbol."""
        print(f"Fetching FMP historical prices for {symbol}")
        url = f"{self.base_url}/historical-price-full/{symbol}"

        request_params = self.params.copy()
        if limit:
            request_params['timeseries'] = limit

        return self._request(url, params=request_params)

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_aftermarket_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the after-market quote for a symbol."""
        print(f"Fetching FMP aftermarket quote for {symbol}")
        url = f"{self.base_url}/quote/{symbol}"
        data = self._request(url, params=self.params)
        return data[0] if data else None

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company profile data, including beta."""
        print(f"Fetching FMP company profile for {symbol}")
        url = f"{self.base_url}/profile/{symbol}"
        data = self._request(url, params=self.params)
        return data[0] if data else None

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_risk_free_rate(self) -> Optional[float]:
        """
        Fetches the latest 3-month Treasury Bill rate as a proxy for the risk-free rate.
        """
        print("Fetching risk-free rate (3-Month Treasury) using FMP v4 endpoint")
        v4_url = 'https://financialmodelingprep.com/api/v4/treasury'

        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)

        request_params = self.params.copy()
        request_params['from'] = from_date.strftime('%Y-%m-%d')
        request_params['to'] = to_date.strftime('%Y-%m-%d')

        data = self._request(v4_url, params=request_params)

        if data and isinstance(data, list):
            latest_record = data[-1]
            rate_value = latest_record.get('month3')

            if rate_value is not None:
                try:
                    print(f"Successfully fetched risk-free rate from API for date: {latest_record.get('date')}")
                    return float(rate_value)
                except (ValueError, TypeError):
                    print(f"Could not convert rate value to float: {rate_value}")

        default_rate = 5.0
        print(f"Warning: Could not fetch risk-free rate from FMP. Using fallback value of {default_rate}%.")
        return default_rate