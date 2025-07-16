from tkinter import messagebox

import time
import requests
import yfinance as yf
import os

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com",
    "User-Agent": "bill hwang"
}

"""Get earnings data from NASDAQ API for a specific date."""
def get_nasdaq_earnings(date: str):
    try:
        url = 'https://api.nasdaq.com/api/calendar/earnings?'
        payload = {"date": date}
        source = requests.get(url=url, headers=headers, params=payload, verify=True)
        data = source.json()
        if not data or 'data' not in data or 'rows' not in data['data']:
            messagebox.showerror("Error", "Failed to fetch NASDAQ earnings data")
            return None
        return data
    except Exception as e:
        messagebox.showerror("Error", f"Error fetching NASDAQ data: {str(e)}")
        return None

"""Get ticker data using yfinance."""
def get_ticker_data_yfinance(symbol: str):
    return yf.Ticker(symbol)

"""Get financial modeling data for a specific symbol."""
def get_fmp_earnings_data(symbol: str, retry_count=3, delay=1.0):
    response = None
    if not os.getenv('FINANCIAL_API_KEY'):
        messagebox.showwarning("Warning", "FINANCIAL_API_KEY not set in environment variables")
        return response

    api_key = os.getenv('FINANCIAL_API_KEY')
    url = f"https://financialmodelingprep.com/stable/earnings?symbol={symbol}&apikey={api_key}"

    for attempt in range(retry_count):
        try:
            # Add delay between requests to avoid rate limiting
            if attempt > 0:
                time.sleep(delay * (attempt + 1))  # Exponential backoff

            response = requests.get(url)

            if response.status_code == 402:  # Payment Required
                print(f"Premium data required for {symbol} - skipping")
                return None

            if response.status_code == 429:  # Too Many Requests
                print(f"Rate limited for {symbol}, attempt {attempt + 1}/{retry_count}")
                continue

            if response.status_code != 200:
                print(f"Error {response.status_code} for {symbol}")
                continue

            return response.json()

        except Exception as e:
            print(f"Error processing {symbol} (attempt {attempt + 1}/{retry_count}): {str(e)}")

    return None