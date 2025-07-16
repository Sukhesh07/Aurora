import tkinter as tk
from tkinter import ttk
import api_requests
from calculations import calculate_earnings_surprise
from formatting import get_detailed_earnings

data = api_requests.get_nasdaq_earnings("2025-07-15")
symbols = [row['symbol'] for row in data['data']['rows']]
earnings_list = get_detailed_earnings(symbols)
#datas = yf.download("JPM", interval="1m", period="1d")
#print(calculate_earnings_surprise(datas))

class StockTable(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title('Lunari')
        self.geometry('1920x1080')

        # Create Treeview
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill='both', expand=True)

        # Define columns
        self.tree['columns'] = ('Symbol', 'Company', 'Market Cap', 'EPS Forecast', 'EPS Actual', 'EPS Surprise',
                                'Price 4:00 am', 'Current Price', 'Price % Δ', 'Δ 1 week', 'Δ 1 Month', 'Δ 1 Year','Overreaction?')

        # Format columns
        self.tree.column('#0', width=0, stretch=tk.NO)  # Hidden column
        self.tree.column('Symbol', anchor=tk.W, width=100)
        self.tree.column('Company', anchor=tk.W, width=300)
        self.tree.column('Market Cap', anchor=tk.E, width=150)
        self.tree.column('EPS Forecast', anchor=tk.E, width=100)
        self.tree.column('EPS Actual', anchor=tk.E, width=100)
        self.tree.column('EPS Surprise', anchor=tk.E, width=100)
        self.tree.column('Price 4:00 am', anchor=tk.E, width=100)
        self.tree.column('Current Price', anchor=tk.E, width=100)
        self.tree.column('Price % Δ', anchor=tk.E, width=100)
        self.tree.column('Δ 1 week', anchor=tk.E, width=100)
        self.tree.column('Δ 1 Month', anchor=tk.E, width=100)
        self.tree.column('Δ 1 Year', anchor=tk.E, width=100)
        self.tree.column('Overreaction?', anchor=tk.E, width=100)

        # Create headings
        self.tree.heading('#0', text='', anchor=tk.W)
        self.tree.heading('Symbol', text='Symbol', anchor=tk.W)
        self.tree.heading('Company', text='Company', anchor=tk.W)
        self.tree.heading('Market Cap', text='Market Cap', anchor=tk.W)
        self.tree.heading('EPS Forecast', text='EPS Forecast', anchor=tk.W)
        self.tree.heading('EPS Actual', text='EPS Actual', anchor=tk.W)
        self.tree.column('EPS Surprise', anchor=tk.E, width=100)
        self.tree.column('Price 4:00 am', anchor=tk.E, width=100)
        self.tree.column('Current Price', anchor=tk.E, width=100)
        self.tree.column('Price % Δ', anchor=tk.E, width=100)
        self.tree.column('Δ 1 week', anchor=tk.E, width=100)
        self.tree.column('Δ 1 Month', anchor=tk.E, width=100)
        self.tree.column('Δ 1 Year', anchor=tk.E, width=100)
        self.tree.column('Overreaction?', anchor=tk.E, width=100)

        # Add data
        for idx, row in enumerate(data['data']['rows']):
            symbol = row['symbol']
            earnings_entry = next((e for e in earnings_list if e['symbol'] == symbol), None)
            eps_pct_change = calculate_earnings_surprise(earnings_entry)

            self.tree.insert(parent='', index='end', iid=str(idx), values=(
                row['symbol'],
                row['name'],
                row['marketCap'],
                earnings_entry['eps_estimated'] if earnings_entry else '',
                earnings_entry['eps_actual'] if earnings_entry else '',
                eps_pct_change,
                '',  # Price 4:00 am - to be filled later
                '',  # Current Price - to be filled later
                '',  # Price % Δ - to be filled later
                '',  # Δ 1 week - to be filled later
                '',  # Δ 1 Month - to be filled later
                '',  # Δ 1 Year - to be filled later
                '',  # Sentiment - to be filled later
                ''  # Overreaction? - to be filled later
            ))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

if __name__ == '__main__':
    app = StockTable()
    app.mainloop()