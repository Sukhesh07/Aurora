import time
import api_requests

def get_detailed_earnings(symbols):
    earnings_list = []

    batch_size = 10  # Process 5 symbols at a time
    batch_delay = 1  # Wait 2 seconds between batches

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]

        for symbol in batch:
            earnings_data = api_requests.get_fmp_earnings_data(symbol)
            if earnings_data:
                for entry in earnings_data:
                    if entry['date'] == '2025-07-15':
                        symbol_earnings = {
                            'symbol': symbol,
                            'eps_actual': entry['epsActual'],
                            'eps_estimated': entry['epsEstimated'],
                            'revenue_actual': entry['revenueActual'],
                            'revenue_estimated': entry['revenueEstimated']
                        }
                        earnings_list.append(symbol_earnings)
                        break

        # Add delay between batches
        if i + batch_size < len(symbols):
            print(f"Waiting between batches... ({i + batch_size}/{len(symbols)} symbols processed)")
            time.sleep(batch_delay)

    return earnings_list

def get_earnings_actual_list(earnings_list):
    eps_actual_list = []
    for earning in earnings_list:
        eps_actual_list.append(earning['eps_actual'])
    return eps_actual_list

def get_earnings_estimated_list(earnings_list):
    eps_estimated_list = []
    for earning in earnings_list:
        eps_estimated_list.append(earning['eps_estimated'])
    return eps_estimated_list

def get_revenue_actual_list(earnings_list):
    revenue_actual_list = []
    for earning in earnings_list:
        revenue_actual_list.append(earning['revenue_actual'])
    return revenue_actual_list

def get_revenue_estimated_list(earnings_list):
    revenue_estimated_list = []
    for earning in earnings_list:
        revenue_estimated_list.append(earning['revenue_estimated'])
    return revenue_estimated_list

def get_earnings_display_list(earnings_list):
    print(f"Collected earnings data for {len(earnings_list)} companies:")
    for earning in earnings_list:
        print(f"\n{earning['symbol']}:")
        print(f"EPS Actual: {earning['eps_actual']}")
        print(f"EPS Estimated: {earning['eps_estimated']}")
        print(f"Revenue Actual: ${earning['revenue_actual']:,}")
        print(f"Revenue Estimated: ${earning['revenue_estimated']:,}")