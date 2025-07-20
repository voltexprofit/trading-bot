"""
Core package for Multi-Exchange Trading Bot
"""

from .bot import MultiExchangeTradingBot
from .user_manager import UserManager
from .exchanges import ExchangeManager
from .trading import TradingEngine

__all__ = [
    'MultiExchangeTradingBot',
    'UserManager',
    'ExchangeManager', 
    'TradingEngine'
]