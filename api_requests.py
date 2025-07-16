from datetime import datetime

from tkinter import messagebox
import time
from ratelimit import limits, sleep_and_retry
import requests
import os
from typing import Optional, Dict, Any, Tuple

# Rate limiting constants
NASDAQ_CALLS = 30  # calls
NASDAQ_PERIOD = 60  # seconds
FMP_CALLS = 10
FMP_PERIOD = 3

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com",
    "User-Agent": "bill hwang"
}

class APIError(Exception):
    """Custom exception for API errors"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


@sleep_and_retry
@limits(calls=NASDAQ_CALLS, period=NASDAQ_PERIOD)
def get_nasdaq_earnings(date: str) -> Optional[Dict[str, Any]]:
    print("getting nasdaq earnings")
    """Get earnings data from NASDAQ API with rate limiting and error handling."""
    try:
        url = 'https://api.nasdaq.com/api/calendar/earnings'
        payload = {"date": date}
        response = requests.get(url=url, headers=headers, params=payload, verify=True)

        if response.status_code == 429:
            messagebox.showerror("Rate Limit Error", "NASDAQ API rate limit reached. Please try again later.")
            return None

        if response.status_code != 200:
            error_msg = f"NASDAQ API Error (Code {response.status_code})"
            messagebox.showerror("Error", error_msg)
            return None

        data = response.json()
        if not data or 'data' not in data or 'rows' not in data['data']:
            messagebox.showerror("Error", "Invalid data format received from NASDAQ API")
            return None

        return data

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Network Error", f"Failed to connect to NASDAQ API: {str(e)}")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        return None


@sleep_and_retry
@limits(calls=FMP_CALLS, period=FMP_PERIOD)
def get_fmp_earnings_data(symbol: str, retry_count: int = 3, delay: float = 1.0) -> Optional[Dict[str, Any]]:
    print("getting fmp earnings data")
    """Get financial modeling data with enhanced rate limiting and error handling."""
    if not os.getenv('FINANCIAL_API_KEY'):
        messagebox.showerror("Error", "FINANCIAL_API_KEY not set in environment variables")
        return None

    api_key = os.getenv('FINANCIAL_API_KEY')
    url = f"https://financialmodelingprep.com/stable/earnings?symbol={symbol}&apikey={api_key}"

    for attempt in range(retry_count):
        try:
            if attempt > 0:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff

            response = requests.get(url)

            error_messages = {
                401: "Invalid API key",
                402: "Premium data required",
                403: "Access forbidden",
                404: "Data not found",
                429: "Rate limit exceeded",
                500: "Internal server error",
                503: "Service unavailable"
            }

            if response.status_code != 200:
                error_msg = error_messages.get(response.status_code, f"Unknown error {response.status_code}")
                if response.status_code == 429:
                    if attempt < retry_count - 1:
                        continue
                messagebox.showerror("API Error", f"{error_msg} for {symbol}")
                return None

            return response.json()

        except requests.exceptions.RequestException as e:
            if attempt == retry_count - 1:
                messagebox.showerror("Network Error", f"Failed to connect to FMP API: {str(e)}")
            continue
        except Exception as e:
            if attempt == retry_count - 1:
                messagebox.showerror("Error", f"Unexpected error processing {symbol}: {str(e)}")
            continue

    return None

@sleep_and_retry
@limits(calls=FMP_CALLS, period=FMP_PERIOD)
def get_recent_price(symbol: str) -> Optional[float]:
    print("getting open close prices")
    """Get latest price with rate limiting and error handling."""
    api_key = os.getenv('FINANCIAL_API_KEY')
    if not api_key:
        messagebox.showerror("Error", "FINANCIAL_API_KEY not set in environment variables")
        return None

    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{symbol}?apikey={api_key}"

    try:
        response = requests.get(url)

        if response.status_code != 200:
            messagebox.showerror("API Error", f"Error {response.status_code} fetching data for {symbol}")
            return None

        data = response.json()
        if not data:
            return None

        return data[0]['close']

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Network Error", f"Failed to fetch price data: {str(e)}")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        return None

@sleep_and_retry
@limits(calls=FMP_CALLS, period=FMP_PERIOD)
def get_price_changes(symbol: str) -> Optional[Dict[str, float]]:
    print("getting price changes")
    """Get price changes with rate limiting and error handling."""
    api_key = os.getenv('FINANCIAL_API_KEY')
    if not api_key:
        messagebox.showerror("Error", "FINANCIAL_API_KEY not set in environment variables")
        return None

    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={api_key}"

    try:
        response = requests.get(url)

        if response.status_code != 200:
            messagebox.showerror("API Error", f"Error {response.status_code} fetching data for {symbol}")
            return None

        data = response.json()
        if not data or 'historical' not in data or not data['historical']:
            messagebox.showerror("Error", f"Invalid or empty data received for {symbol}")
            return None

        historical = data['historical']
        current_price = historical[0]['close'] if historical else None

        changes = {}

        # 1 week change
        if len(historical) >= 5:  # 5 trading days
            week_ago_price = historical[5]['close']
            changes['1w'] = ((current_price - week_ago_price) / week_ago_price) * 100

        # 1 month change
        if len(historical) >= 22:  # ~22 trading days
            month_ago_price = historical[22]['close']
            changes['1m'] = ((current_price - month_ago_price) / month_ago_price) * 100

        # 3 month change
        if len(historical) >= 66:  # ~66 trading days
            three_month_price = historical[66]['close']
            changes['3m'] = ((current_price - three_month_price) / three_month_price) * 100

        # 1 year change
        if len(historical) >= 252:  # ~252 trading days
            year_ago_price = historical[252]['close']
            changes['1y'] = ((current_price - year_ago_price) / year_ago_price) * 100

        return changes

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Network Error", f"Failed to fetch price changes: {str(e)}")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        return None

@sleep_and_retry
@limits(calls=FMP_CALLS, period=FMP_PERIOD)
def get_aftermarket_quote(symbol: str) -> Optional[float]:
    """Get after-market ask price for a given stock symbol.
    Args:
        symbol (str): The stock symbol to get after-market data for
    Returns:
        Optional[float]: The current ask price, or None if unavailable
    """
    print("getting aftermarket quote")
    api_key = os.getenv('FINANCIAL_API_KEY')
    if not api_key:
        messagebox.showerror("Error", "FINANCIAL_API_KEY not set in environment variables")
        return None
    url = f"https://financialmodelingprep.com/stable/aftermarket-quote?symbol={symbol}&apikey={api_key}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            messagebox.showerror("API Error", f"Error {response.status_code} fetching after-market data for {symbol}")
            return None
        data = response.json()
        if not data or len(data) == 0:
            print(f"No after-market data available for {symbol}")
            return None
        quote = data[0]  # Get first item from the list
        return quote.get('askPrice')
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Network Error", f"Failed to fetch after-market data: {str(e)}")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        return None

@sleep_and_retry
@limits(calls=FMP_CALLS, period=FMP_PERIOD)
def get_yesterday_close(symbol: str) -> Optional[float]:
    print("getting yesterday's closing price")
    """Get yesterday's closing price for a given stock symbol.
    Args:
        symbol (str): The stock symbol to get the closing price for
    Returns:
        Optional[float]: Yesterday's closing price, or None if unavailable
    """
    api_key = os.getenv('FINANCIAL_API_KEY')
    if not api_key:
        messagebox.showerror("Error", "FINANCIAL_API_KEY not set in environment variables")
        return None

    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={api_key}"

    try:
        response = requests.get(url)
        if response.status_code != 200:
            messagebox.showerror("API Error", f"Error {response.status_code} fetching yesterday's close for {symbol}")
            return None

        data = response.json()
        if not data or 'historical' not in data or len(data['historical']) < 2:
            print(f"No historical data available for {symbol}")
            return None

        # Get yesterday's close from the second entry (index 1)
        # since the first entry (index 0) is today
        return data['historical'][1]['close']

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Network Error", f"Failed to fetch yesterday's closing price: {str(e)}")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        return None
