"""
Trading logic for the Multi-Exchange Trading Bot
Implements dynamic 0.2% balance martingale strategy
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from config.settings import MIN_BALANCE, PRICE_DROP_TRIGGER
from utils import (
    setup_logger, log_trade, log_error,
    calculate_position_size, calculate_weighted_average_entry,
    should_take_profit, should_add_martingale_level,
    calculate_profit_percentage, calculate_margin_return,
    validate_trade_parameters, format_percentage, format_currency
)
from core.exchanges import ExchangeManager

logger = setup_logger('trading')

class TradingEngine:
    """Handles all trading operations and strategy logic"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
    
    def process_user_trading(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """
        Process trading logic for individual user
        
        Args:
            user_id: User ID
            user_data: User data dictionary
            
        Returns:
            True if processing successful
        """
        try:
            # Skip if not setup or not enabled
            if not user_data.get('setup_complete') or not user_data.get('trading_enabled'):
                return True
            
            # Skip if safe stop requested and no active position
            if user_data.get('safe_stop_requested') and not user_data.get('is_active'):
                return True
            
            exchange = user_data.get('exchange')
            if not exchange:
                return False
            
            # Update balance and recalculate strategy
            self.update_balance_strategy(user_id, user_data)
            
            # Auto-continue trading cycles
            if not user_data.get('is_active') and not user_data.get('safe_stop_requested') and not user_data.get('trade_in_progress'):
                logger.info(f"User {user_id}: Starting new cycle")
                success = self.start_new_cycle(user_id, user_data)
                if success:
                    time.sleep(30)  # Wait before next cycle
                return success
            
            # Monitor existing positions
            if user_data.get('is_active'):
                # Check take profit
                if self.check_take_profit(user_id, user_data):
                    logger.info(f"User {user_id}: Take profit triggered")
                    return self.close_position(user_id, user_data)
                
                # Check martingale levels
                if self.should_add_martingale(user_id, user_data):
                    logger.info(f"User {user_id}: Adding martingale level")
                    return self.add_martingale_level(user_id, user_data)
            
            return True
            
        except Exception as e:
            log_error(logger, e, f"Error processing trading for user {user_id}", user_id=user_id)
            return False
    
    def update_balance_strategy(self, user_id: int, user_data: Dict[str, Any]):
        """Update user's balance and recalculate martingale strategy"""
        try:
            exchange = user_data['exchange']
            exchange_type = user_data['exchange_type']
            
            # Get current balance
            current_balance = self.exchange_manager.get_balance(exchange, exchange_type)
            
            # Only update if balance changed significantly (>1% change)
            last_balance = user_data.get('current_balance', 0)
            if abs(current_balance - last_balance) / max(last_balance, 1) > 0.01:
                
                from utils.calculations import calculate_dynamic_martingale_sequence
                from config.settings import calculate_base_amount
                
                # Update base amount and martingale sequence
                new_base_amount = calculate_base_amount(current_balance)
                new_sequence = calculate_dynamic_martingale_sequence(current_balance)
                
                user_data['current_balance'] = current_balance
                user_data['base_amount'] = new_base_amount
                user_data['martingale_sequence'] = new_sequence
                user_data['last_balance_update'] = datetime.now()
                
                logger.info(f"User {user_id}: Updated strategy - Balance: ${current_balance:.2f}, Base: ${new_base_amount:.4f}")
                
        except Exception as e:
            log_error(logger, e, f"Error updating balance strategy for user {user_id}")
    
    def start_new_cycle(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Start a new martingale cycle"""
        try:
            # Prevent duplicate trades
            if user_data.get('trade_in_progress') or user_data.get('is_active'):
                return False
            
            user_data['trade_in_progress'] = True
            
            exchange = user_data['exchange']
            exchange_type = user_data['exchange_type']
            symbol = user_data['symbol']
            leverage = user_data['leverage']
            
            # Set leverage
            self.exchange_manager.set_leverage(exchange, exchange_type, symbol, leverage)
            
            # Get current price
            current_price = self.exchange_manager.get_price(exchange, symbol)
            if not current_price:
                user_data['trade_in_progress'] = False
                return False
            
            # Check balance
            balance = self.exchange_manager.get_balance(exchange, exchange_type)
            if balance < MIN_BALANCE:
                logger.error(f"User {user_id}: Insufficient balance ${balance:.2f}")
                user_data['trade_in_progress'] = False
                return False
            
            # Calculate position size for first level
            margin_amount = user_data['martingale_sequence'][0]
            
            # Validate trade parameters
            is_valid, error_msg = validate_trade_parameters(balance, margin_amount, leverage, current_price)
            if not is_valid:
                logger.error(f"User {user_id}: Trade validation failed - {error_msg}")
                user_data['trade_in_progress'] = False
                return False
            
            position_size = calculate_position_size(margin_amount, leverage, current_price)
            
            # Place buy order
            order = self.exchange_manager.place_market_order(
                exchange, exchange_type, symbol, 'buy', position_size, user_id
            )
            
            if order:
                # Update user state
                user_data['current_step'] = 0
                user_data['entry_price'] = current_price
                user_data['position_side'] = 'buy'
                user_data['is_active'] = True
                
                # Initialize position tracking
                user_data['position_levels'] = [{
                    'price': current_price,
                    'margin': margin_amount,
                    'contracts': position_size,
                    'level': 1,
                    'timestamp': datetime.now()
                }]
                
                # Reset tracking
                user_data['martingale_trigger_prices'] = []
                
                # Record trade
                self.record_trade(user_id, user_data, 'open_level_1', current_price, 
                                position_size, margin_amount)
                
                log_trade(logger, user_id, 'cycle_started', 
                         price=current_price, amount=position_size, 
                         margin=margin_amount, cycle=user_data['cycle_count'] + 1)
                
                user_data['trade_in_progress'] = False
                return True
            else:
                user_data['trade_in_progress'] = False
                return False
                
        except Exception as e:
            user_data['trade_in_progress'] = False
            log_error(logger, e, f"Error starting cycle for user {user_id}")
            return False
    
    def check_take_profit(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Check if position should take profit"""
        try:
            exchange = user_data['exchange']
            symbol = user_data['symbol']
            
            current_price = self.exchange_manager.get_price(exchange, symbol)
            if not current_price:
                return False
            
            weighted_avg_entry = calculate_weighted_average_entry(user_data['position_levels'])
            if not weighted_avg_entry:
                return False
            
            take_profit_pct = user_data['take_profit_pct']
            
            result = should_take_profit(current_price, weighted_avg_entry, take_profit_pct)
            
            if result:
                profit_pct = calculate_profit_percentage(current_price, weighted_avg_entry)
                logger.info(f"User {user_id}: Take profit triggered - {profit_pct:.2f}% profit")
            
            return result
            
        except Exception as e:
            log_error(logger, e, f"Error checking take profit for user {user_id}")
            return False
    
    def should_add_martingale(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Check if should add martingale level"""
        try:
            exchange = user_data['exchange']
            symbol = user_data['symbol']
            
            current_price = self.exchange_manager.get_price(exchange, symbol)
            if not current_price:
                return False
            
            # Check if we've reached max levels
            if user_data['current_step'] >= len(user_data['martingale_sequence']) - 1:
                return False
            
            # Determine reference price
            if user_data['current_step'] == 0:
                reference_price = user_data['entry_price']
            else:
                trigger_prices = user_data.get('martingale_trigger_prices', [])
                reference_price = trigger_prices[-1] if trigger_prices else user_data['entry_price']
            
            if not reference_price:
                return False
            
            return should_add_martingale_level(current_price, reference_price, PRICE_DROP_TRIGGER)
            
        except Exception as e:
            log_error(logger, e, f"Error checking martingale for user {user_id}")
            return False
    
    def add_martingale_level(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Add martingale level to position"""
        try:
            exchange = user_data['exchange']
            exchange_type = user_data['exchange_type']
            symbol = user_data['symbol']
            leverage = user_data['leverage']
            
            current_price = self.exchange_manager.get_price(exchange, symbol)
            if not current_price:
                return False
            
            # Move to next step
            user_data['current_step'] += 1
            step = user_data['current_step']
            
            # Calculate position size for this level
            margin_amount = user_data['martingale_sequence'][step]
            position_size = calculate_position_size(margin_amount, leverage, current_price)
            
            # Check balance
            balance = self.exchange_manager.get_balance(exchange, exchange_type)
            if balance < margin_amount:
                logger.error(f"User {user_id}: Insufficient balance for martingale level {step + 1}")
                user_data['current_step'] -= 1  # Revert step
                return False
            
            # Place buy order
            order = self.exchange_manager.place_market_order(
                exchange, exchange_type, symbol, 'buy', position_size, user_id
            )
            
            if order:
                # Record trigger price
                user_data['martingale_trigger_prices'].append(current_price)
                
                # Add to position levels
                user_data['position_levels'].append({
                    'price': current_price,
                    'margin': margin_amount,
                    'contracts': position_size,
                    'level': step + 1,
                    'timestamp': datetime.now()
                })
                
                # Record trade
                self.record_trade(user_id, user_data, f'martingale_{step + 1}', 
                                current_price, position_size, margin_amount)
                
                log_trade(logger, user_id, 'martingale_added', 
                         level=step + 1, price=current_price, amount=position_size)
                
                return True
            else:
                user_data['current_step'] -= 1  # Revert step
                return False
                
        except Exception as e:
            log_error(logger, e, f"Error adding martingale level for user {user_id}")
            if 'current_step' in user_data:
                user_data['current_step'] = max(0, user_data['current_step'] - 1)
            return False
    
    def close_position(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Close user position with take profit"""
        try:
            exchange = user_data['exchange']
            exchange_type = user_data['exchange_type']
            symbol = user_data['symbol']
            
            # Get actual position size from exchange
            actual_position_size = self.exchange_manager.get_position_size(exchange, exchange_type, symbol)
            
            if actual_position_size <= 0:
                logger.warning(f"User {user_id}: No position found to close")
                return False
            
            current_price = self.exchange_manager.get_price(exchange, symbol)
            if not current_price:
                return False
            
            # Place sell order (reduce only)
            order = self.exchange_manager.place_market_order(
                exchange, exchange_type, symbol, 'sell', actual_position_size, 
                user_id, reduce_only=True
            )
            
            if order:
                # Calculate profits
                weighted_avg_entry = calculate_weighted_average_entry(user_data['position_levels'])
                total_margin = sum(level['margin'] for level in user_data['position_levels'])
                
                if weighted_avg_entry:
                    profit_pct = calculate_profit_percentage(current_price, weighted_avg_entry)
                    margin_return = calculate_margin_return(profit_pct, user_data['leverage'])
                    profit_usd = total_margin * (margin_return / 100)
                else:
                    profit_pct = 0
                    margin_return = 0
                    profit_usd = 0
                
                # Record closing trade
                self.record_trade(user_data, user_data, 'close_all_tp', current_price, 
                                actual_position_size, 0, profit_usd)
                
                # Update cycle tracking
                user_data['cycle_count'] += 1
                user_data['total_profit'] += margin_return
                
                # Reset for new cycle
                user_data['is_active'] = False
                user_data['entry_price'] = None
                user_data['current_step'] = 0
                user_data['position_levels'] = []
                user_data['martingale_trigger_prices'] = []
                
                log_trade(logger, user_id, 'cycle_completed', 
                         profit_pct=profit_pct, profit_usd=profit_usd, 
                         cycle=user_data['cycle_count'])
                
                return True
            else:
                return False
                
        except Exception as e:
            log_error(logger, e, f"Error closing position for user {user_id}")
            return False
    
    def emergency_close_position(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Emergency close user position"""
        try:
            exchange = user_data['exchange']
            exchange_type = user_data['exchange_type']
            symbol = user_data['symbol']
            
            # Get actual position size
            actual_position_size = self.exchange_manager.get_position_size(exchange, exchange_type, symbol)
            
            if actual_position_size <= 0:
                return True  # No position to close
            
            # Place emergency sell order
            order = self.exchange_manager.place_market_order(
                exchange, exchange_type, symbol, 'sell', actual_position_size, 
                user_id, reduce_only=True
            )
            
            if order:
                # Reset user state
                user_data['is_active'] = False
                user_data['trading_enabled'] = False
                user_data['entry_price'] = None
                user_data['current_step'] = 0
                user_data['position_levels'] = []
                user_data['martingale_trigger_prices'] = []
                
                log_trade(logger, user_id, 'emergency_close', amount=actual_position_size)
                return True
            
            return False
            
        except Exception as e:
            log_error(logger, e, f"Error emergency closing position for user {user_id}")
            return False
    
    def record_trade(self, user_id: int, user_data: Dict[str, Any], trade_type: str, 
                    price: float, amount: float, margin_used: float, profit_usd: float = 0):
        """Record trade in user's history"""
        try:
            # Increment trade counter for opening trades
            if trade_type.startswith('open_') or trade_type.startswith('martingale_'):
                user_data['total_trades'] += 1
                trade_id = user_data['total_trades']
            else:
                trade_id = None
            
            # Get current balance
            balance = 0
            try:
                exchange = user_data.get('exchange')
                exchange_type = user_data.get('exchange_type')
                if exchange and exchange_type:
                    balance = self.exchange_manager.get_balance(exchange, exchange_type)
            except:
                pass
            
            trade_record = {
                'trade_id': trade_id,
                'timestamp': datetime.now(),
                'type': trade_type,
                'price': price,
                'amount': amount,
                'margin_used': margin_used,
                'profit_usd': profit_usd,
                'cycle_number': user_data.get('cycle_count', 0) + 1,
                'balance_after': balance,
                'exchange': user_data.get('exchange_type', ''),
                'symbol': user_data.get('symbol', '')
            }
            
            # Add to trade history for closing trades
            if trade_type.startswith('close') or trade_type.startswith('emergency') or profit_usd != 0:
                if 'closed_trades' not in user_data:
                    user_data['closed_trades'] = []
                user_data['closed_trades'].append(trade_record)
            
        except Exception as e:
            log_error(logger, e, f"Error recording trade for user {user_id}")
    
    def get_user_trading_status(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive trading status for user"""
        try:
            exchange = user_data.get('exchange')
            exchange_type = user_data.get('exchange_type', '')
            symbol = user_data.get('symbol', '')
            
            status = {
                'user_id': user_id,
                'exchange': exchange_type,
                'symbol': symbol,
                'setup_complete': user_data.get('setup_complete', False),
                'trading_enabled': user_data.get('trading_enabled', False),
                'is_active': user_data.get('is_active', False),
                'safe_stop_requested': user_data.get('safe_stop_requested', False),
                'current_balance': 0,
                'current_price': 0,
                'position_info': {},
                'cycle_count': user_data.get('cycle_count', 0),
                'total_trades': user_data.get('total_trades', 0),
                'total_profit': user_data.get('total_profit', 0),
            }
            
            if exchange and exchange_type:
                # Get current balance and price
                status['current_balance'] = self.exchange_manager.get_balance(exchange, exchange_type)
                status['current_price'] = self.exchange_manager.get_price(exchange, symbol) or 0
                
                # Get position info if active
                if user_data.get('is_active'):
                    status['position_info'] = self.exchange_manager.get_position_info(exchange, exchange_type, symbol)
                    status['weighted_avg_entry'] = calculate_weighted_average_entry(user_data.get('position_levels', []))
                    status['current_step'] = user_data.get('current_step', 0)
                    status['max_steps'] = len(user_data.get('martingale_sequence', []))
            
            return status
            
        except Exception as e:
            log_error(logger, e, f"Error getting trading status for user {user_id}")
            return {'error': str(e)}
    
    def validate_user_for_trading(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate if user can start trading"""
        try:
            if not user_data.get('setup_complete'):
                return False, "Setup not complete"
            
            if not user_data.get('exchange'):
                return False, "Exchange not connected"
            
            exchange = user_data['exchange']
            exchange_type = user_data['exchange_type']
            
            balance = self.exchange_manager.get_balance(exchange, exchange_type)
            if balance < MIN_BALANCE:
                return False, f"Insufficient balance: ${balance:.2f} (minimum ${MIN_BALANCE})"
            
            # Check if symbol is valid
            symbol = user_data['symbol']
            if not self.exchange_manager.validate_symbol(exchange, symbol):
                return False, f"Invalid trading symbol: {symbol}"
            
            return True, "Ready to trade"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"