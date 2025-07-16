import os
from typing import Optional, Dict, Any, List

import requests
from ratelimit import limits, sleep_and_retry


# --- Configuration ---

class ApiConfig:
    # Rate limiting
    NASDAQ_CALLS = 30
    NASDAQ_PERIOD = 60
    FMP_CALLS = 10
    FMP_PERIOD = 3

    # Base URLs
    NASDAQ_BASE_URL = 'https://api.nasdaq.com/api'
    FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'
    # The 'stable' URL is likely deprecated and has been removed from this version.
    # FMP_STABLE_URL = 'https://financialmodelingprep.com/stable'


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
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            if not data:
                # Handle cases where the API returns an empty but successful response
                return None
            return data

        except requests.exceptions.HTTPError as http_err:
            raise APIError(status_code=http_err.response.status_code, message=str(http_err)) from http_err
        except requests.exceptions.RequestException as req_err:
            # Handle network-related errors
            raise APIError(status_code=503, message=f"Network error: {req_err}") from req_err


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
        # Removed stable_url as it's likely deprecated.

    def _build_url(self, base_url: str, path: str) -> str:
        return f"{base_url}/{path}?apikey={self.api_key}"

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_earnings_data(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """Get historical earnings data for a specific symbol."""
        print(f"Fetching FMP earnings for {symbol}")
        # FIX: Changed to use the v3 API base URL and the correct endpoint for earnings surprises.
        url = self._build_url(self.base_url, f"earnings-surprises/{symbol}")
        return self._request(url)

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_historical_price_full(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get full historical daily price data for a symbol."""
        print(f"Fetching FMP historical prices for {symbol}")
        url = self._build_url(self.base_url, f"historical-price-full/{symbol}")
        return self._request(url)

    @sleep_and_retry
    @limits(calls=ApiConfig.FMP_CALLS, period=ApiConfig.FMP_PERIOD)
    def get_aftermarket_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the after-market quote for a symbol."""
        print(f"Fetching FMP aftermarket quote for {symbol}")
        # FIX: Changed to use the v3 API base URL and a more standard quote endpoint.
        url = self._build_url(self.base_url, f"quote/{symbol}")
        data = self._request(url)
        return data[0] if data else None
