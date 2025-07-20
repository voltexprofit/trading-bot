
"""
Trading calculation utilities for the Multi-Exchange Trading Bot
"""

from typing import List, Dict, Optional
from config.settings import (
    BALANCE_PERCENTAGE, 
    LEVERAGE, 
    TAKE_PROFIT_PCT,
    PRICE_DROP_TRIGGER,
    get_martingale_sequence,
    calculate_base_amount
)

def calculate_dynamic_martingale_sequence(balance: float) -> List[float]:
    """
    Calculate martingale sequence based on 0.2% of account balance
    
    Args:
        balance: User's account balance
        
    Returns:
        List of margin amounts for each martingale level
    """
    base_amount = calculate_base_amount(balance)
    return get_martingale_sequence(base_amount)

def calculate_position_size(margin_amount: float, leverage: int, price: float) -> float:
    """
    Calculate position size in contracts
    
    Args:
        margin_amount: Margin amount to use
        leverage: Leverage multiplier
        price: Current asset price
        
    Returns:
        Position size in contracts
    """
    position_value = margin_amount * leverage
    position_size = position_value / price
    return round(position_size, 6)

def calculate_weighted_average_entry(position_levels: List[Dict]) -> Optional[float]:
    """
    Calculate weighted average entry price from position levels
    
    Args:
        position_levels: List of position level dictionaries
        
    Returns:
        Weighted average entry price or None
    """
    if not position_levels:
        return None
    
    total_contracts = sum(level['contracts'] for level in position_levels)
    if total_contracts <= 0:
        return None
    
    weighted_sum = sum(level['price'] * level['contracts'] for level in position_levels)
    return weighted_sum / total_contracts

def calculate_profit_percentage(current_price: float, entry_price: float) -> float:
    """
    Calculate profit percentage
    
    Args:
        current_price: Current asset price
        entry_price: Entry price
        
    Returns:
        Profit percentage
    """
    if entry_price <= 0:
        return 0
    
    return (current_price - entry_price) / entry_price * 100

def calculate_margin_return(profit_pct: float, leverage: int) -> float:
    """
    Calculate margin return percentage
    
    Args:
        profit_pct: Price profit percentage
        leverage: Leverage multiplier
        
    Returns:
        Margin return percentage
    """
    return profit_pct * leverage

def should_take_profit(current_price: float, weighted_avg_entry: float, 
                      take_profit_pct: float = TAKE_PROFIT_PCT) -> bool:
    """
    Check if position should take profit
    
    Args:
        current_price: Current asset price
        weighted_avg_entry: Weighted average entry price
        take_profit_pct: Take profit percentage threshold
        
    Returns:
        True if should take profit
    """
    if not weighted_avg_entry or weighted_avg_entry <= 0:
        return False
    
    profit_pct = calculate_profit_percentage(current_price, weighted_avg_entry)
    return profit_pct >= take_profit_pct

def should_add_martingale_level(current_price: float, reference_price: float,
                               drop_trigger: float = PRICE_DROP_TRIGGER) -> bool:
    """
    Check if should add martingale level based on price drop
    
    Args:
        current_price: Current asset price
        reference_price: Reference price for comparison
        drop_trigger: Price drop percentage trigger
        
    Returns:
        True if should add martingale level
    """
    if not reference_price or reference_price <= 0:
        return False
    
    drop_pct = (reference_price - current_price) / reference_price * 100
    return drop_pct >= drop_trigger

def calculate_total_risk(martingale_sequence: List[float]) -> float:
    """
    Calculate total risk from martingale sequence
    
    Args:
        martingale_sequence: List of margin amounts
        
    Returns:
        Total risk amount
    """
    return sum(martingale_sequence)

def calculate_safety_ratio(balance: float, total_risk: float) -> float:
    """
    Calculate safety ratio (balance / total_risk)
    
    Args:
        balance: Account balance
        total_risk: Total risk amount
        
    Returns:
        Safety ratio
    """
    if total_risk <= 0:
        return float('inf')
    
    return balance / total_risk

def calculate_roi(current_balance: float, starting_balance: float) -> float:
    """
    Calculate Return on Investment (ROI)
    
    Args:
        current_balance: Current account balance
        starting_balance: Starting account balance
        
    Returns:
        ROI percentage
    """
    if starting_balance <= 0:
        return 0
    
    return (current_balance - starting_balance) / starting_balance * 100

def validate_trade_parameters(balance: float, margin_amount: float, 
                             leverage: int, price: float) -> tuple[bool, str]:
    """
    Validate trade parameters before placing order
    
    Args:
        balance: Account balance
        margin_amount: Margin amount for trade
        leverage: Leverage multiplier
        price: Asset price
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if balance <= 0:
        return False, "Invalid balance"
    
    if margin_amount <= 0:
        return False, "Invalid margin amount"
    
    if margin_amount > balance:
        return False, "Insufficient balance for margin"
    
    if leverage < 1 or leverage > 100:
        return False, "Invalid leverage"
    
    if price <= 0:
        return False, "Invalid price"
    
    return True, ""

def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format percentage with specified decimals
    
    Args:
        value: Percentage value
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value:.{decimals}f}%"

def format_currency(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """
    Format currency with specified symbol and decimals
    
    Args:
        value: Currency value
        symbol: Currency symbol
        decimals: Number of decimal places
        
    Returns:
        Formatted currency string
    """
    return f"{symbol}{value:.{decimals}f}"