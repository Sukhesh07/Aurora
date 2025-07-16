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

def detect_overreaction(
    earnings_surprise_pct: float,
    open_price: float,
    close_price: float,
    recent_closes: list[float],
    surprise_weight: float = 0.5,
    volatility_multiplier: float = 2.0
) -> bool:
    """
    Detects if a stock had a market overreaction after earnings.

    Parameters:
    - earnings_surprise_pct: (float) EPS surprise in percent (e.g., 12.5 for +12.5%)
    - open_price: (float) Price at market open (9:30am)
    - close_price: (float) Price at close (4:00pm)
    - recent_closes: (list) List of recent close prices (e.g., past 20 days)
    - surprise_weight: (float) Factor market normally reacts to earnings (default: 0.5)
    - volatility_multiplier: (float) Threshold to classify outlier moves (default: 2.0)

    Returns:
    - True if market likely overreacted, else False
    """

    # Intraday price change (%)
    intraday_move = ((close_price - open_price) / open_price) * 100

    # Expected move based on surprise
    expected_move = earnings_surprise_pct * surprise_weight

    # Deviation from expected
    move_delta = abs(intraday_move - expected_move)

    # Calculate historical volatility (%)
    returns = np.diff(recent_closes) / recent_closes[:-1]
    daily_volatility = np.std(returns) * 100  # in percent

    # Overreaction if move is significantly outside expected bounds
    if move_delta > (volatility_multiplier * daily_volatility):
        return True
    return False