import tkinter as tk
from tkinter import ttk, messagebox
from api_requests import NasdaqApiClient, FmpApiClient, APIError
from calculations import calculate_earnings_surprise, determine_overreaction
from typing import List, Dict, Any, Optional


def _process_historical_data(historical: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Processes raw historical data to extract key price points and changes."""
    if not historical:
        return {'previous_close': None, '1w': None, '1m': None, '3m': None, '1y': None}

    current_price = historical[0]['close']

    def get_change(days_ago):
        if len(historical) > days_ago:
            past_price = historical[days_ago]['close']
            return ((current_price - past_price) / past_price) * 100
        return None

    return {
        'previous_close': historical[1]['close'] if len(historical) > 1 else None,
        '1w': get_change(5),  # 5 trading days
        '1m': get_change(22),  # ~22 trading days
        '3m': get_change(66),  # ~66 trading days
        '1y': get_change(252),  # ~252 trading days
    }


def fetch_and_process_data(symbols: List[str]) -> List[Dict[str, Any]]:
    """Fetches and processes all required financial data for a list of symbols."""
    fmp_client = FmpApiClient()
    processed_data = []

    for symbol in symbols:
        try:
            print(f"--- Processing {symbol} ---")
            # 1. Fetch all data for the symbol
            earnings_history = fmp_client.get_earnings_data(symbol)
            historical_data = fmp_client.get_historical_price_full(symbol)
            aftermarket_quote = fmp_client.get_aftermarket_quote(symbol)

            # 2. Process earnings data
            earnings_entry = None
            if earnings_history:
                for entry in earnings_history:
                    # FINAL FIX: Use the correct keys from the API response log.
                    if entry.get('date', '').startswith('2025-07-15'):
                        earnings_entry = {
                            'eps_actual': entry.get('actualEarningResult'),
                            'eps_estimated': entry.get('estimatedEarning'),
                        }
                        break

            # 3. Process price data
            price_info = _process_historical_data(historical_data.get('historical', []) if historical_data else [])
            # FINAL FIX: The key 'price' is correct as per the log.
            current_price = aftermarket_quote.get('price') if aftermarket_quote else None

            # 4. Assemble the data for the UI
            processed_data.append({
                'symbol': symbol,
                'earnings': earnings_entry,
                'prices': price_info,
                'current_price': current_price,
            })
        except APIError as e:
            print(f"Could not fetch data for {symbol}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {symbol}: {e}")

    return processed_data


class StockTable(tk.Tk):
    def __init__(self, nasdaq_data: List[Dict[str, Any]], all_stock_data: List[Dict[str, Any]]):
        super().__init__()
        self.title('Aurora')
        self.geometry('1920x1080')

        self._setup_treeview()
        self._populate_data(nasdaq_data, all_stock_data)

    def _setup_treeview(self):
        """Configures the Treeview widget."""
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill='both', expand=True)
        self.tree['show'] = 'headings'

        columns = ('Symbol', 'Company', 'Market Cap', 'EPS Forecast', 'EPS Actual', 'EPS Surprise', 'Previous Close',
                   'Current Price', 'Price % Change', 'Change 1 week', '1 Month', '3 Month', '1 Year', 'Overreaction?')
        self.tree['columns'] = columns

        for col in columns:
            self.tree.heading(col, text=col)
            width = 200 if col == 'Company' else 80 if col == 'Symbol' else 100
            self.tree.column(col, anchor='center', width=width)

        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _populate_data(self, nasdaq_data: List[Dict[str, Any]], all_stock_data: List[Dict[str, Any]]):
        """Fills the Treeview with stock data."""
        data_map = {item['symbol']: item for item in all_stock_data}

        for idx, nasdaq_row in enumerate(nasdaq_data):
            symbol = nasdaq_row['symbol']
            stock_data = data_map.get(symbol)

            if not stock_data:
                continue

            # Extract data for clarity
            earnings = stock_data.get('earnings', {}) or {}
            prices = stock_data.get('prices', {}) or {}
            current_price = stock_data.get('current_price')
            previous_close = prices.get('previous_close')

            # Perform calculations
            eps_surprise_float = calculate_earnings_surprise(earnings)
            eps_surprise_str = f"{eps_surprise_float:.2f}%" if eps_surprise_float is not None else ''

            price_change = ((
                                        current_price - previous_close) / previous_close * 100) if previous_close and current_price else None

            overreaction = determine_overreaction(eps_surprise_float,
                                                  price_change) if eps_surprise_float is not None and price_change is not None else ''

            # Format for display
            def fmt_pct(value):
                return f"{value:.2f}%" if value is not None else ''

            def fmt_currency(value):
                return f"${value:.2f}" if value is not None else ''

            self.tree.insert(parent='', index='end', iid=str(idx), values=(
                symbol,
                nasdaq_row.get('name', ''),
                nasdaq_row.get('marketCap', ''),
                earnings.get('eps_estimated', ''),
                earnings.get('eps_actual', ''),
                eps_surprise_str,
                fmt_currency(previous_close),
                fmt_currency(current_price),
                fmt_pct(price_change),
                fmt_pct(prices.get('1w')),
                fmt_pct(prices.get('1m')),
                fmt_pct(prices.get('3m')),
                fmt_pct(prices.get('1y')),
                overreaction
            ))


if __name__ == '__main__':
    try:
        # Initial data load from NASDAQ
        nasdaq_client = NasdaqApiClient()
        nasdaq_earnings_data = nasdaq_client.get_earnings("2025-07-15")

        if not nasdaq_earnings_data:
            raise APIError(status_code=0, message="No data returned from NASDAQ.")

        nasdaq_rows = nasdaq_earnings_data['data']['rows']
        symbols_to_fetch = [row['symbol'] for row in nasdaq_rows if row and row.get('symbol')]

        # Fetch detailed data for all symbols
        all_stock_data = fetch_and_process_data(symbols_to_fetch)

        # Create and run the application
        app = StockTable(nasdaq_rows, all_stock_data)
        app.mainloop()

    except APIError as e:
        messagebox.showerror("Fatal API Error", f"Could not start the application.\nError: {e.message}")
    except Exception as e:
        messagebox.showerror("Fatal Error", f"An unexpected error occurred: {e}")