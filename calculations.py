import numpy as np

def calculate_intraday_change(data):
    open_price = data.between_time("13:30", "13:30")['Open'].values[0]
    close_price = data.between_time("19:59", "19:59")['Close'].values[0]
    change = np.float64(((close_price - open_price) / open_price) * 100)
    return f"{change.item():.2f}%"

def calculate_earnings_surprise(earnings_entry):
    # Calculate EPS % change if we have both actual and estimated
    eps_pct_change = ''
    if earnings_entry and earnings_entry['eps_actual'] and earnings_entry['eps_estimated']:
        eps_pct_change = ((earnings_entry['eps_actual'] - earnings_entry['eps_estimated']) / abs(
            earnings_entry['eps_estimated'])) * 100 if earnings_entry['eps_estimated'] != 0 else 0
        eps_pct_change = f"{eps_pct_change:.2f}%"
    return eps_pct_change

def determine_overreaction(eps_surprise, price_change):
    """
    Determine if the price change is an overreaction compared to the EPS surprise
    """
    try:
        if abs(float(price_change)) > abs(float(eps_surprise)) * 2:
            return "Yes"
        return "No"
    except (ValueError, TypeError):
        return ""