import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from api_requests import NasdaqApiClient, FmpApiClient, APIError
from calculations import calculate_earnings_surprise, calculate_abnormal_return, determine_overreaction, \
    calculate_price_change
from typing import List, Dict, Any, Optional


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
            print(f"\n--- [DEBUG] Processing Symbol: {symbol} ---")
            # 1. Fetch all data for the symbol
            earnings_history = fmp_client.get_earnings_data(symbol)
            historical_data = fmp_client.get_historical_price_full(symbol)
            aftermarket_quote = fmp_client.get_aftermarket_quote(symbol)
            company_profile = fmp_client.get_company_profile(symbol)

            # 2. Process earnings data
            print(f"[DEBUG] Searching for earnings on date: {earnings_date}")
            print(f"[DEBUG] Full earnings history for {symbol}: {earnings_history}")

            earnings_entry = next((
                {'eps_actual': e.get('actualEarningResult'), 'eps_estimated': e.get('estimatedEarning')}
                for e in (earnings_history or []) if e.get('date', '') == earnings_date
            ), None)

            print(f"[DEBUG] Found earnings entry for {symbol}: {earnings_entry}")

            # 3. Process price data
            current_price = aftermarket_quote.get('price') if aftermarket_quote else None
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

        columns = ('Symbol', 'Company', 'Market Cap', 'EPS Forecast', 'EPS Actual', 'EPS Surprise', 'Prev Close',
                   'Curr Price', 'Price Change', 'Abnormal Ret', 'Overreaction?')
        self.tree['columns'] = columns

        for col in columns:
            self.tree.heading(col, text=col)
            width = 180 if col == 'Company' else 110 if col == 'Market Cap' else 100
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
            current_price = stock_data.get('current_price')
            previous_close = stock_data.get('prices', {}).get('previous_close')

            # --- Perform Calculations ---
            eps_surprise_float = calculate_earnings_surprise(earnings)
            actual_return = calculate_price_change(current_price, previous_close)

            abnormal_return = calculate_abnormal_return(
                actual_return=actual_return,
                market_return=stock_data.get('market_return'),
                beta=stock_data.get('beta'),
                risk_free_rate=stock_data.get('risk_free_rate')
            )

            overreaction = determine_overreaction(abnormal_return, eps_surprise_float)

            # --- Format for display ---
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
                fmt_pct(eps_surprise_float),
                fmt_currency(previous_close),
                fmt_currency(current_price),
                fmt_pct(actual_return),
                fmt_pct(abnormal_return),  # The new key metric!
                overreaction
            ))


if __name__ == '__main__':
    try:
        nasdaq_client = NasdaqApiClient()
        fmp_client = FmpApiClient()

        # 1. Get market-wide data once before processing symbols
        market_data = _process_market_data(fmp_client)
        if market_data.get('market_return') is None or market_data.get('risk_free_rate') is None:
            raise APIError(status_code=0,
                           message="Could not fetch critical market-wide data (SPY return or Risk-Free Rate).")

        # 2. Get the list of symbols with earnings today
        today_str = datetime.now().strftime('%Y-%m-%d')
        nasdaq_earnings_data = nasdaq_client.get_earnings(today_str)
        if not nasdaq_earnings_data:
            raise APIError(status_code=0, message="No data returned from NASDAQ.")
        nasdaq_rows = nasdaq_earnings_data['data']['rows']
        symbols_to_fetch = [row['symbol'] for row in nasdaq_rows if row and row.get('symbol')]

        # 3. Fetch detailed data for all symbols, passing in today's date
        all_stock_data = fetch_and_process_data(symbols_to_fetch, market_data, today_str)

        # 4. Create and run the application
        app = StockTable(nasdaq_rows, all_stock_data)
        app.mainloop()

    except APIError as e:
        messagebox.showerror("Fatal API Error", f"Could not start the application.\nError: {e.message}")
    except Exception as e:
        messagebox.showerror("Fatal Error", f"An unexpected error occurred: {e}")