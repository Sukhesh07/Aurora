from typing import Optional, Dict

def calculate_price_change(current_price: Optional[float], previous_price: Optional[float]) -> Optional[float]:
    """
    Calculates the percentage change between a current and previous price.
    Returns the result as a float, or None if inputs are invalid.
    """
    if current_price is None or previous_price is None or previous_price == 0:
        return None
    return ((current_price - previous_price) / previous_price) * 100

def calculate_earnings_surprise(earnings_entry: Optional[Dict[str, Optional[float]]]) -> Optional[float]:
    """
    Calculates the EPS surprise percentage from an earnings data dictionary.
    Returns the raw float value, or None if calculation is not possible.
    """
    if not earnings_entry:
        return None

    eps_actual = earnings_entry.get('eps_actual')
    eps_estimated = earnings_entry.get('eps_estimated')

    if eps_actual is None or eps_estimated is None:
        return None

    if eps_estimated == 0:
        # If the estimate was 0, any surprise is technically infinite.
        # Following the original logic's implication to return 0 in this case.
        return 0.0

    return ((eps_actual - eps_estimated) / abs(eps_estimated)) * 100

def determine_overreaction(eps_surprise: Optional[float], price_change: Optional[float]) -> str:
    """
    Determines if a price change is an overreaction to an EPS surprise.
    An overreaction is defined as the absolute price change being more than
    double the absolute EPS surprise.
    """
    if eps_surprise is None or price_change is None:
        return ""

    # If there's no surprise, any price change is not an overreaction *to the surprise*.
    if abs(eps_surprise) == 0:
        return "No"

    if abs(price_change) > abs(eps_surprise) * 2:
        return "Yes"

    return "No"
