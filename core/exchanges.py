"""
Exchange connection and trading handlers for the Multi-Exchange Trading Bot
FIXED VERSION - Corrected order placement function
"""

import ccxt
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal, ROUND_DOWN

from config.settings import EXCHANGE_SETTINGS, DEFAULT_SYMBOLS
from utils import setup_logger, log_error, log_trade

logger = setup_logger('exchanges')

class ExchangeManager:
    """Manages exchange connections and trading operations"""
    
    def __init__(self, sandbox: bool = True):
        self.sandbox = sandbox
        
    def create_exchange_instance(self, exchange_type: str, api_key: str, 
                               secret: str) -> Tuple[bool, Any]:
        """
        Create and test exchange instance
        
        Args:
            exchange_type: 'binance' or 'bybit'
            api_key: API key
            secret: Secret key
            
        Returns:
            Tuple of (success, exchange_instance_or_error)
        """
        try:
            exchange_type = exchange_type.lower()
            
            if exchange_type == 'binance':
                exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': secret,
                    'sandbox': self.sandbox,
                    **EXCHANGE_SETTINGS['binance']
                })
                
            elif exchange_type == 'bybit':
                exchange = ccxt.bybit({
                    'apiKey': api_key,
                    'secret': secret,
                    'password': '',  # Bybit doesn't use passphrase
                    'sandbox': self.sandbox,
                    **EXCHANGE_SETTINGS['bybit']
                })
                
            else:
                return False, f"Unsupported exchange: {exchange_type}"
            
            # Test connection
            try:
                exchange.load_markets()
                balance = self.get_balance(exchange, exchange_type)
                logger.info(f"Successfully connected to {exchange_type}")
                return True, exchange
                
            except Exception as test_error:
                log_error(logger, test_error, f"Exchange connection test failed for {exchange_type}")
                return False, f"Connection test failed: {str(test_error)}"
                
        except Exception as e:
            log_error(logger, e, f"Error creating {exchange_type} instance")
            return False, f"Failed to create exchange instance: {str(e)}"
    
    def get_balance(self, exchange: ccxt.Exchange, exchange_type: str) -> float:
        """
        Get USDT balance from exchange
        
        Args:
            exchange: Exchange instance
            exchange_type: Exchange type
            
        Returns:
            USDT balance
        """
        try:
            if exchange_type == 'binance':
                balance = exchange.fetch_balance({'type': 'future'})
                if 'USDT' in balance and 'free' in balance['USDT']:
                    return float(balance['USDT']['free'])
                    
            elif exchange_type == 'bybit':
                # Try different account types for Bybit
                for account_type in ['unified', 'contract', None]:
                    try:
                        params = {'type': account_type} if account_type else {}
                        balance = exchange.fetch_balance(params)
                        
                        if 'USDT' in balance and 'free' in balance['USDT']:
                            return float(balance['USDT']['free'])
                    except:
                        continue
            
            return 0.0
            
        except Exception as e:
            log_error(logger, e, f"Error fetching balance from {exchange_type}")
            return 0.0
    
    def get_price(self, exchange: ccxt.Exchange, symbol: str) -> Optional[float]:
        """
        Get current price for symbol
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            
        Returns:
            Current price or None
        """
        try:
            ticker = exchange.fetch_ticker(symbol)
            return float(ticker['last']) if ticker['last'] else None
            
        except Exception as e:
            log_error(logger, e, f"Error fetching price for {symbol}")
            return None
    
    def set_leverage(self, exchange: ccxt.Exchange, exchange_type: str, 
                    symbol: str, leverage: int) -> bool:
        """
        Set leverage for symbol
        
        Args:
            exchange: Exchange instance
            exchange_type: Exchange type
            symbol: Trading symbol
            leverage: Leverage amount
            
        Returns:
            True if successful
        """
        try:
            if exchange_type == 'binance':
                exchange.set_leverage(leverage, symbol)
                
            elif exchange_type == 'bybit':
                exchange.set_leverage(leverage, symbol, params={'category': 'linear'})
            
            logger.info(f"Set leverage {leverage}x for {symbol} on {exchange_type}")
            return True
            
        except Exception as e:
            log_error(logger, e, f"Error setting leverage on {exchange_type}")
            return False
    
    def place_market_order(self, exchange: ccxt.Exchange, exchange_type: str,
                          symbol: str, side: str, amount: float, 
                          user_id: int, reduce_only: bool = False) -> Optional[Dict]:
        """
        Place market order - FIXED VERSION
        
        Args:
            exchange: Exchange instance
            exchange_type: Exchange type
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount
            user_id: User ID for logging
            reduce_only: Whether this is a reduce-only order
            
        Returns:
            Order result or None
        """
        try:
            # Round amount to appropriate precision
            amount = self.round_amount(amount, exchange_type)
            
            if amount <= 0:
                logger.warning(f"Invalid order amount: {amount}")
                return None
            
            params = {}
            
            if exchange_type == 'binance':
                params['type'] = 'MARKET'
                if reduce_only:
                    params['reduceOnly'] = True
                    
                # FIXED: Correct number of arguments for create_market_order
                order = exchange.create_market_order(symbol, side, amount, None, params)
                
            elif exchange_type == 'bybit':
                params['category'] = 'linear'
                if reduce_only:
                    params['reduceOnly'] = True
                    
                # FIXED: Correct number of arguments for create_market_order
                order = exchange.create_market_order(symbol, side, amount, None, params)
            
            # Log successful trade
            log_trade(logger, user_id, 'order_placed', 
                     exchange=exchange_type, symbol=symbol, side=side, 
                     amount=amount, reduce_only=reduce_only)
            
            logger.info(f"Order placed: {side} {amount} {symbol} on {exchange_type}")
            return order
            
        except Exception as e:
            log_error(logger, e, f"Error placing {side} order on {exchange_type}", 
                     user_id=user_id, symbol=symbol, amount=amount)
            return None
    
    def get_position_size(self, exchange: ccxt.Exchange, exchange_type: str,
                         symbol: str) -> float:
        """
        Get current position size
        
        Args:
            exchange: Exchange instance
            exchange_type: Exchange type
            symbol: Trading symbol
            
        Returns:
            Position size in contracts
        """
        try:
            if exchange_type == 'binance':
                positions = exchange.fetch_positions([symbol])
                
            elif exchange_type == 'bybit':
                positions = exchange.fetch_positions([symbol], params={'category': 'linear'})
            
            for position in positions:
                if position['contracts'] and position['contracts'] > 0:
                    return float(position['contracts'])
            
            return 0.0
            
        except Exception as e:
            log_error(logger, e, f"Error fetching position for {symbol} on {exchange_type}")
            return 0.0
    
    def get_position_info(self, exchange: ccxt.Exchange, exchange_type: str,
                         symbol: str) -> Dict[str, Any]:
        """
        Get detailed position information
        
        Args:
            exchange: Exchange instance
            exchange_type: Exchange type
            symbol: Trading symbol
            
        Returns:
            Position information dictionary
        """
        try:
            if exchange_type == 'binance':
                positions = exchange.fetch_positions([symbol])
                
            elif exchange_type == 'bybit':
                positions = exchange.fetch_positions([symbol], params={'category': 'linear'})
            
            for position in positions:
                if position['contracts'] and position['contracts'] > 0:
                    return {
                        'size': float(position['contracts']),
                        'side': position['side'],
                        'entry_price': float(position['entryPrice']) if position['entryPrice'] else 0,
                        'mark_price': float(position['markPrice']) if position['markPrice'] else 0,
                        'unrealized_pnl': float(position['unrealizedPnl']) if position['unrealizedPnl'] else 0,
                        'percentage': float(position['percentage']) if position['percentage'] else 0
                    }
            
            return {
                'size': 0,
                'side': None,
                'entry_price': 0,
                'mark_price': 0,
                'unrealized_pnl': 0,
                'percentage': 0
            }
            
        except Exception as e:
            log_error(logger, e, f"Error fetching position info for {symbol} on {exchange_type}")
            return {
                'size': 0,
                'side': None,
                'entry_price': 0,
                'mark_price': 0,
                'unrealized_pnl': 0,
                'percentage': 0
            }
    
    def round_amount(self, amount: float, exchange_type: str) -> float:
        """
        Round amount to exchange-specific precision
        
        Args:
            amount: Amount to round
            exchange_type: Exchange type
            
        Returns:
            Rounded amount
        """
        try:
            if exchange_type == 'binance':
                # Binance typically uses 6 decimal places for amounts
                return float(Decimal(str(amount)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
                
            elif exchange_type == 'bybit':
                # Bybit typically uses 4 decimal places for amounts
                return float(Decimal(str(amount)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN))
            
            return round(amount, 6)
            
        except Exception as e:
            log_error(logger, e, f"Error rounding amount for {exchange_type}")
            return round(amount, 6)
    
    def validate_symbol(self, exchange: ccxt.Exchange, symbol: str) -> bool:
        """
        Validate if symbol is available on exchange
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            
        Returns:
            True if symbol is valid
        """
        try:
            markets = exchange.load_markets()
            return symbol in markets
            
        except Exception as e:
            log_error(logger, e, f"Error validating symbol {symbol}")
            return False
    
    def get_symbol_info(self, exchange: ccxt.Exchange, symbol: str) -> Dict[str, Any]:
        """
        Get symbol trading information
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            
        Returns:
            Symbol information dictionary
        """
        try:
            markets = exchange.load_markets()
            
            if symbol in markets:
                market = markets[symbol]
                return {
                    'symbol': symbol,
                    'base': market['base'],
                    'quote': market['quote'],
                    'active': market['active'],
                    'type': market['type'],
                    'spot': market['spot'],
                    'margin': market['margin'],
                    'future': market['future'],
                    'option': market['option'],
                    'swap': market['swap'],
                    'contract': market['contract'],
                    'linear': market.get('linear'),
                    'inverse': market.get('inverse'),
                    'taker': market['taker'],
                    'maker': market['maker'],
                    'contract_size': market.get('contractSize'),
                    'precision': market['precision'],
                    'limits': market['limits']
                }
            
            return {}
            
        except Exception as e:
            log_error(logger, e, f"Error getting symbol info for {symbol}")
            return {}
    
    def close_exchange_connection(self, exchange: ccxt.Exchange) -> bool:
        """
        Properly close exchange connection
        
        Args:
            exchange: Exchange instance
            
        Returns:
            True if successful
        """
        try:
            if hasattr(exchange, 'close'):
                exchange.close()
            return True
            
        except Exception as e:
            log_error(logger, e, "Error closing exchange connection")
            return False