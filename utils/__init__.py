"""
Utilities package for Multi-Exchange Trading Bot
"""

from .logger import setup_logger, log_trade, log_user_action, log_error
from .calculations import (
    calculate_dynamic_martingale_sequence,
    calculate_position_size,
    calculate_weighted_average_entry,
    calculate_profit_percentage,
    calculate_margin_return,
    should_take_profit,
    should_add_martingale_level,
    calculate_total_risk,
    calculate_safety_ratio,
    calculate_roi,
    validate_trade_parameters,
    format_percentage,
    format_currency
)
from .data_manager import DataManager

__all__ = [
    'setup_logger',
    'log_trade', 
    'log_user_action',
    'log_error',
    'calculate_dynamic_martingale_sequence',
    'calculate_position_size',
    'calculate_weighted_average_entry',
    'calculate_profit_percentage', 
    'calculate_margin_return',
    'should_take_profit',
    'should_add_martingale_level',
    'calculate_total_risk',
    'calculate_safety_ratio',
    'calculate_roi',
    'validate_trade_parameters',
    'format_percentage',
    'format_currency',
    'DataManager'
]