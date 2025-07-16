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
        return 0.0
    return ((eps_actual - eps_estimated) / abs(eps_estimated)) * 100


def calculate_abnormal_return(
    actual_return: Optional[float],
    market_return: Optional[float],
    beta: Optional[float],
    risk_free_rate: Optional[float]
) -> Optional[float]:
    """
    Calculates the abnormal return using the Capital Asset Pricing Model (CAPM).
    Abnormal Return = Actual Return - Expected Return
    Expected Return = Risk-Free Rate + Beta * (Market Return - Risk-Free Rate)

    All inputs should be in percentage terms (e.g., 1.5 for 1.5%).
    """
    if actual_return is None or market_return is None or beta is None or risk_free_rate is None:
        return None

    # CAPM formula to find the return we *expect* from the stock
    expected_return = risk_free_rate + beta * (market_return - risk_free_rate)

    # Abnormal return is the difference between what actually happened and what was expected
    abnormal_return = actual_return - expected_return
    return abnormal_return


def determine_overreaction(
    abnormal_return: Optional[float],
    eps_surprise: Optional[float],
    overreaction_threshold: float = 2.0
) -> str:
    """
    Determines if a stock's abnormal return constitutes an overreaction to an EPS surprise.

    An overreaction is defined as the abnormal return being disproportionately
    large compared to the magnitude of the earnings surprise.
    """
    if abnormal_return is None or eps_surprise is None:
        return ""

    if abs(eps_surprise) == 0:
        # If there's no surprise, any significant abnormal return is an overreaction.
        return "Yes" if abs(abnormal_return) > 1.0 else "No"  # Using 1% as a threshold for "significant"

    # The core logic: Is the abnormal move more than twice the size of the surprise?
    is_disproportionate = abs(abnormal_return) > abs(eps_surprise) * overreaction_threshold

    # Further check: ensure the reaction is in the same direction as the surprise.
    # A positive surprise should have a positive reaction, and vice versa.
    # The sign of the product will be positive if they are in the same direction.
    is_logical_direction = (abnormal_return * eps_surprise) >= 0

    if is_disproportionate and is_logical_direction:
        return "Yes"
    # Could add more categories here, like "Anomalous" for reactions in the wrong direction.
    return "No"