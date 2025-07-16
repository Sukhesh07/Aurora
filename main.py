import tkinter as tk
from tkinter import ttk
import api_requests
from api_requests import get_aftermarket_quote, get_yesterday_close
from calculations import calculate_earnings_surprise, determine_overreaction
from formatting import get_detailed_earnings

data = api_requests.get_nasdaq_earnings("2025-07-15")
symbols = [row['symbol'] for row in data['data']['rows']]
earnings_list = get_detailed_earnings(symbols)

class StockTable(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title('Aurora')
        self.geometry('1920x1080')

        # Create Treeview
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill='both', expand=True)

        # Show headings
        self.tree['show'] = 'headings'

        # Define columns
        columns = ('Symbol', 'Company', 'Market Cap', 'EPS Forecast', 'EPS Actual', 'EPS Surprise', 'Previous Close',
                   'Current Price', 'Price % Change', 'Change 1 week', '1 Month',
                   '3 Month', '1 Year', 'Overreaction?')
        self.tree['columns'] = columns

        # Configure column headings
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=100)  # Add default width

            # Customize widths for specific columns
            if col in ['Company']:
                self.tree.column(col, width=200)  # Wider for company names
            elif col in ['Symbol']:
                self.tree.column(col, width=80)  # Narrower for symbols

        # Add data
        for idx, row in enumerate(data['data']['rows']):
            symbol = row['symbol']
            earnings_entry = next((e for e in earnings_list if e['symbol'] == symbol), None)
            eps_pct_change = calculate_earnings_surprise(earnings_entry)

            # Get price data
            current_price = get_aftermarket_quote(symbol)
            previous_close_price = get_yesterday_close(symbol)
            
            price_change = ((current_price - previous_close_price) / previous_close_price * 100) if previous_close_price and current_price else None

            # Get historical price changes
            changes = api_requests.get_price_changes(symbol)

            # Convert eps_pct_change to float if it's a percentage string
            if isinstance(eps_pct_change, str):
                try:
                    eps_pct_change = float(eps_pct_change.strip('%'))
                except (ValueError, AttributeError):
                    eps_pct_change = None

            self.tree.insert(parent='', index='end', iid=str(idx), values=(
                row['symbol'],
                row['name'],
                row['marketCap'],
                earnings_entry['eps_estimated'] if earnings_entry else '',
                earnings_entry['eps_actual'] if earnings_entry else '',
                f"{eps_pct_change:.2f}%" if eps_pct_change is not None else '',
                f"${previous_close_price:.2f}" if previous_close_price  else '',
                f"${current_price:.2f}" if current_price else '',
                f"{price_change:.2f}%" if price_change is not None else '',
                f"{changes['1w']:.2f}%" if changes and '1w' in changes else '',
                f"{changes['1m']:.2f}%" if changes and '1m' in changes else '',
                f"{changes['3m']:.2f}%" if changes and '3m' in changes else '',
                f"{changes['1y']:.2f}%" if changes and '1y' in changes else '',
                determine_overreaction(eps_pct_change, price_change) if eps_pct_change is not None and price_change is not None else ''
            ))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

if __name__ == '__main__':
    app = StockTable()
    app.mainloop()