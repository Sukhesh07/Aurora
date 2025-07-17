import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from api_requests import NasdaqApiClient, FmpApiClient, APIError
from calculations import calculate_earnings_surprise, calculate_abnormal_return, determine_overreaction, \
    calculate_price_change
from typing import List, Dict, Any, Optional
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


def _process_market_data(fmp_client: FmpApiClient) -> Dict[str, Optional[float]]:
    """Fetches and calculates market-wide data needed for CAPM."""
    market_data = {'market_return': None, 'risk_free_rate': None}

    # 1. Get market return using SPY as a proxy
    spy_history_data = fmp_client.get_historical_price_full('SPY', limit=5)
    if spy_history_data and spy_history_data.get('historical') and len(spy_history_data['historical']) > 1:
        historical = spy_history_data['historical']
        market_data['market_return'] = calculate_price_change(historical[0]['close'], historical[1]['close'])

    # 2. Get risk-free rate
    market_data['risk_free_rate'] = fmp_client.get_risk_free_rate()

    return market_data


def fetch_and_process_data(symbols: List[str], market_data: Dict[str, Optional[float]], earnings_date: str) -> List[
    Dict[str, Any]]:
    """Fetches and processes all required financial data for a list of symbols."""
    fmp_client = FmpApiClient()
    processed_data = []

    for symbol in symbols:
        try:
            #print(f"\n--- [DEBUG] Processing Symbol: {symbol} ---")
            # 1. Fetch all data for the symbol
            earnings_history = fmp_client.get_earnings_data(symbol)
            historical_data = fmp_client.get_historical_price_full(symbol)
            aftermarket_quote = fmp_client.get_aftermarket_quote(symbol)
            company_profile = fmp_client.get_company_profile(symbol)

            # 2. Process earnings data
            #print(f"[DEBUG] Searching for earnings on date: {earnings_date}")
            #print(f"[DEBUG] Full earnings history for {symbol}: {earnings_history}")

            earnings_entry = next((
                {'eps_actual': e.get('actualEarningResult'), 'eps_estimated': e.get('estimatedEarning')}
                for e in (earnings_history or []) if e.get('date', '') == earnings_date
            ), None)

            #print(f"[DEBUG] Found earnings entry for {symbol}: {earnings_entry}")

            # 3. Process price data
            current_price = aftermarket_quote
            previous_close = historical_data['historical'][1]['close'] if historical_data and historical_data.get(
                'historical') and len(historical_data['historical']) > 1 else None
            price_info = {'previous_close': previous_close}

            # 4. Assemble the data for the UI
            processed_data.append({
                'symbol': symbol,
                'earnings': earnings_entry,
                'prices': price_info,
                'current_price': current_price,
                'beta': company_profile.get('beta') if company_profile else None,
                **market_data
            })
        except APIError as e:
            print(f"Warning: Could not fetch all data for {symbol}: {e}")
        except Exception as e:
            print(f"Warning: An unexpected error occurred while processing {symbol}: {e}")

    return processed_data


class StockTable(ttk.Window):
    def __init__(self):
        super().__init__(themename='superhero')
        self.title('Aurora')
        self.geometry('1920x1080')

        self.nasdaq_client = NasdaqApiClient()
        self.fmp_client = FmpApiClient()

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        """Configures the main UI layout, including the refresh button and treeview."""
        container = ttk.Frame(self, padding=10)
        container.pack(fill=BOTH, expand=YES)

        controls_frame = ttk.Frame(container)
        controls_frame.pack(side=TOP, fill=X, pady=(0, 10))

        refresh_button = ttk.Button(
            controls_frame,
            text="Refresh Data",
            command=self.refresh_data,
            bootstyle="outline-success"
        )
        refresh_button.pack(side=LEFT)

        tree_container = ttk.Frame(container)
        tree_container.pack(fill=BOTH, expand=YES)

        columns = ('Symbol', 'Company', 'Market Cap', 'EPS Forecast', 'EPS Actual', 'EPS Surprise', 'Prev Close',
                   'Curr Price', 'Price Change', 'Abnormal Ret', 'Overreaction?')

        self.tree = ttk.Treeview(
            master=tree_container,
            columns=columns,
            show='headings',
            bootstyle='primary'
        )

        for col in columns:
            self.tree.heading(col, text=col)
            width = 180 if col == 'Company' else 110 if col == 'Market Cap' else 100
            self.tree.column(col, anchor='center', width=width)

        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)

        scrollbar = ttk.Scrollbar(tree_container, orient=VERTICAL, command=self.tree.yview, bootstyle='round-primary')
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.tag_configure('positive', foreground='#4CAF50')
        self.tree.tag_configure('negative', foreground='#F44336')

    def refresh_data(self):
        """Fetches fresh data from APIs and repopulates the table."""
        try:
            self.title("Aurora - Refreshing...")
            self.update_idletasks()

            market_data = _process_market_data(self.fmp_client)
            if market_data.get('market_return') is None or market_data.get('risk_free_rate') is None:
                raise APIError(status_code=0,
                               message="Could not fetch critical market-wide data (SPY return or Risk-Free Rate).")

            today_str = datetime.now().strftime('%Y-%m-%d')
            nasdaq_earnings_data = self.nasdaq_client.get_earnings(today_str)
            if not nasdaq_earnings_data:
                raise APIError(status_code=0, message="No data returned from NASDAQ.")

            nasdaq_rows = nasdaq_earnings_data['data']['rows']
            symbols_to_fetch = [row['symbol'] for row in nasdaq_rows if row and row.get('symbol')]

            all_stock_data = fetch_and_process_data(symbols_to_fetch, market_data, today_str)

            self._populate_data(nasdaq_rows, all_stock_data)

        except APIError as e:
            messagebox.showerror("API Error", f"Could not refresh data.\nError: {e.message}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during refresh: {e}")
        finally:
            self.title("Aurora")

    def _populate_data(self, nasdaq_data: List[Dict[str, Any]], all_stock_data: List[Dict[str, Any]]):
        """Clears and fills the Treeview with stock data."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        data_map = {item['symbol']: item for item in all_stock_data}

        for idx, nasdaq_row in enumerate(nasdaq_data):
            symbol = nasdaq_row['symbol']
            stock_data = data_map.get(symbol)

            if not stock_data:
                continue

            earnings = stock_data.get('earnings', {}) or {}
            current_price = stock_data.get('current_price')
            previous_close = stock_data.get('prices', {}).get('previous_close')

            eps_surprise_float = calculate_earnings_surprise(earnings)
            actual_return = calculate_price_change(current_price, previous_close)

            abnormal_return = calculate_abnormal_return(
                actual_return=actual_return,
                market_return=stock_data.get('market_return'),
                beta=stock_data.get('beta'),
                risk_free_rate=stock_data.get('risk_free_rate')
            )

            overreaction = determine_overreaction(abnormal_return, eps_surprise_float)

            def fmt_pct(value):
                return f"{value:.2f}%" if value is not None else ''

            def fmt_currency(value):
                return f"${value:.2f}" if value is not None else ''

            tags = []
            if actual_return is not None:
                tags.append('positive' if actual_return >= 0 else 'negative')

            self.tree.insert(parent='', index='end', iid=str(idx), values=(
                symbol,
                nasdaq_row.get('name', ''),
                nasdaq_row.get('marketCap', ''),
                earnings.get('eps_estimated', ''),
                earnings.get('eps_actual', ''),
                fmt_pct(eps_surprise_float),
                fmt_currency(previous_close),
                fmt_currency(current_price),
                fmt_pct(actual_return),
                fmt_pct(abnormal_return),
                overreaction
            ), tags=tags)


if __name__ == '__main__':
    try:
        # Data fetching and processing is now handled within the StockTable class.
        # We just need to create an instance of the app and run it.
        app = StockTable()
        app.mainloop()

    except APIError as e:
        messagebox.showerror("Fatal API Error", f"Could not start the application.\nError: {e.message}")
    except Exception as e:
        messagebox.showerror("Fatal Error", f"An unexpected error occurred: {e}")