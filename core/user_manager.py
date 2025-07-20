"""
User management for the Multi-Exchange Trading Bot
"""

from datetime import datetime
from typing import Dict, Set, Optional, Any

from config.settings import (
    AUTHORIZATION_CODE, 
    DEFAULT_SYMBOLS, 
    LEVERAGE, 
    TAKE_PROFIT_PCT,
    calculate_base_amount
)
from utils import DataManager, setup_logger, log_user_action, calculate_dynamic_martingale_sequence

logger = setup_logger('user_manager')

class UserManager:
    """Manages user data, authentication, and initialization"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.users: Dict[int, Dict[str, Any]] = {}
        self.authorized_users: Set[int] = set()
        
        # Load existing data
        self.load_all_data()
    
    def load_all_data(self):
        """Load all user data on startup"""
        try:
            # Load authorized users
            self.authorized_users = self.data_manager.load_authorized_users()
            
            # Load individual user data
            for user_id in self.authorized_users:
                user_data = self.data_manager.load_user_data(user_id)
                if user_data:
                    self.users[user_id] = user_data
                else:
                    # Initialize if data missing
                    self.initialize_new_user(user_id)
                    
            logger.info(f"Loaded data for {len(self.users)} users")
            
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def authorize_user(self, user_id: int, username: str, first_name: str, 
                      auth_code: str) -> tuple[bool, str]:
        """
        Authorize a new user
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            auth_code: Authorization code provided
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if auth_code != AUTHORIZATION_CODE:
                log_user_action(logger, user_id, 'auth_failed', 
                              reason='invalid_code', code=auth_code)
                return False, "❌ Invalid authorization code."
            
            if user_id in self.authorized_users:
                return True, "✅ You are already authorized!"
            
            # Add to authorized users
            self.authorized_users.add(user_id)
            
            # Initialize user data
            self.initialize_new_user(user_id)
            self.users[user_id]['username'] = username or ''
            self.users[user_id]['first_name'] = first_name or ''
            self.users[user_id]['authorized'] = True
            
            # Save data
            self.save_user_data(user_id)
            self.save_authorized_users()
            
            log_user_action(logger, user_id, 'authorized', 
                          username=username, first_name=first_name)
            
            welcome_msg = f"✅ Welcome {first_name}!\n\n"
            welcome_msg += "🤖 Multi-Exchange Trading Bot v2.0\n"
            welcome_msg += "📊 Dynamic 0.2% Balance Strategy\n"
            welcome_msg += "🏢 Choose your exchange to get started:\n\n"
            welcome_msg += "🟡 Binance - Global futures exchange\n"
            welcome_msg += "🟠 Bybit - Advanced derivatives platform\n\n"
            welcome_msg += "Click an exchange button below!"
            
            return True, welcome_msg
            
        except Exception as e:
            logger.error(f"Error authorizing user {user_id}: {e}")
            return False, "❌ Authorization error occurred."
    
    def initialize_new_user(self, user_id: int):
        """Initialize a new user with default settings"""
        try:
            # Calculate initial martingale sequence with default balance
            default_balance = 100.0  # Will be updated when real balance is known
            base_amount = calculate_base_amount(default_balance)
            
            self.users[user_id] = {
                # Authentication & Setup
                'authorized': False,
                'setup_complete': False,
                'exchange_selected': False,
                'waiting_for_api_key': False,
                'waiting_for_secret': False,
                
                # Exchange Configuration
                'api_key': '',
                'secret': '',
                'exchange_type': '',
                'exchange': None,
                'symbol': '',
                
                # Trading Configuration
                'leverage': LEVERAGE,
                'take_profit_pct': TAKE_PROFIT_PCT,
                'balance_percentage': 0.002,  # 0.2%
                'base_amount': base_amount,
                'martingale_sequence': calculate_dynamic_martingale_sequence(default_balance),
                
                # Trading State
                'current_step': 0,
                'entry_price': None,
                'position_side': None,
                'is_active': False,
                'safe_stop_requested': False,
                'trading_enabled': False,
                'start_button_pressed': False,
                'trade_in_progress': False,
                'position_levels': [],
                'martingale_trigger_prices': [],
                
                # Analytics & Statistics
                'cycle_count': 0,
                'total_trades': 0,
                'total_profit': 0,
                'closed_trades': [],
                'balance_history': [],
                'starting_balance': None,
                'current_balance': 0,
                'last_balance_update': datetime.now(),
                
                # Performance Tracking
                'daily_returns': {},
                'weekly_returns': {},
                'monthly_returns': {},
                'profit_history': [],
                'daily_profits': {},
                'best_cycle': 0,
                'worst_cycle': 0,
                'consecutive_wins': 0,
                'max_win_streak': 0,
                'win_rate': 0,
                'average_cycle_time': 0,
                
                # User Information
                'username': '',
                'first_name': '',
                'created_at': datetime.now(),
                'last_active': datetime.now(),
                'session_start_time': datetime.now(),
                
                # Temporary Setup Data
                'temp_api_key': '',
                'temp_exchange_type': ''
            }
            
            logger.info(f"Initialized new user {user_id}")
            
        except Exception as e:
            logger.error(f"Error initializing user {user_id}: {e}")
    
    def update_user_balance_strategy(self, user_id: int, balance: float):
        """
        Update user's martingale sequence based on current balance
        
        Args:
            user_id: User ID
            balance: Current account balance
        """
        try:
            if user_id not in self.users:
                return
            
            # Calculate new base amount (0.2% of balance)
            new_base_amount = calculate_base_amount(balance)
            
            # Update martingale sequence
            new_sequence = calculate_dynamic_martingale_sequence(balance)
            
            # Update user data
            self.users[user_id]['base_amount'] = new_base_amount
            self.users[user_id]['martingale_sequence'] = new_sequence
            self.users[user_id]['current_balance'] = balance
            self.users[user_id]['last_balance_update'] = datetime.now()
            
            # Set starting balance if not set
            if self.users[user_id]['starting_balance'] is None:
                self.users[user_id]['starting_balance'] = balance
            
            logger.info(f"Updated balance strategy for user {user_id}: "
                       f"${balance:.2f} -> base ${new_base_amount:.4f}")
            
        except Exception as e:
            logger.error(f"Error updating balance strategy for user {user_id}: {e}")
    
    def select_exchange(self, user_id: int, exchange_type: str) -> tuple[bool, str]:
        """
        Select exchange for user
        
        Args:
            user_id: User ID
            exchange_type: 'binance' or 'bybit'
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if user_id not in self.users:
                return False, "❌ User not found. Please authorize first."
            
            exchange_type = exchange_type.lower()
            if exchange_type not in ['binance', 'bybit']:
                return False, "❌ Invalid exchange. Choose 'binance' or 'bybit'."
            
            # Update user data
            self.users[user_id]['exchange_type'] = exchange_type
            self.users[user_id]['exchange_selected'] = True
            self.users[user_id]['symbol'] = DEFAULT_SYMBOLS[exchange_type]
            
            self.save_user_data(user_id)
            
            log_user_action(logger, user_id, 'exchange_selected', 
                          exchange=exchange_type)
            
            exchange_name = "Binance" if exchange_type == 'binance' else "Bybit"
            emoji = "🟡" if exchange_type == 'binance' else "🟠"
            
            success_msg = f"{emoji} {exchange_name} Selected!\n\n"
            success_msg += "📋 Next Steps:\n"
            success_msg += f"1. Get your {exchange_name} API credentials\n"
            success_msg += "2. Use: /setapi YOUR_API_KEY YOUR_SECRET\n"
            success_msg += "3. Click 🚀 Start to begin trading\n\n"
            
            if exchange_type == 'binance':
                success_msg += "📍 Binance API Requirements:\n"
                success_msg += "• Enable Futures Trading\n"
                success_msg += "• Enable Spot & Margin Trading\n"
                success_msg += "• Restrict to your IP (recommended)\n"
            else:
                success_msg += "📍 Bybit API Requirements:\n"
                success_msg += "• Enable Derivatives Trading\n"
                success_msg += "• Enable Wallet/Account Read\n"
                success_msg += "• Restrict to your IP (recommended)\n"
            
            success_msg += "\n⚙️ Use 'Setup' for detailed instructions!"
            
            return True, success_msg
            
        except Exception as e:
            logger.error(f"Error selecting exchange for user {user_id}: {e}")
            return False, "❌ Error selecting exchange."
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id in self.authorized_users
    
    def is_setup_complete(self, user_id: int) -> bool:
        """Check if user setup is complete"""
        return (user_id in self.users and 
                self.users[user_id].get('setup_complete', False))
    
    def get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data dictionary"""
        return self.users.get(user_id)
    
    def update_user_info(self, user_id: int, username: str = None, 
                        first_name: str = None):
        """Update user information"""
        if user_id in self.users:
            if username is not None:
                self.users[user_id]['username'] = username
            if first_name is not None:
                self.users[user_id]['first_name'] = first_name
            
            self.users[user_id]['last_active'] = datetime.now()
    
    def save_user_data(self, user_id: int) -> bool:
        """Save user data to file"""
        if user_id in self.users:
            return self.data_manager.save_user_data(user_id, self.users[user_id])
        return False
    
    def save_authorized_users(self) -> bool:
        """Save authorized users to file"""
        return self.data_manager.save_authorized_users(self.authorized_users)
    
    def get_authorized_users_count(self) -> int:
        """Get count of authorized users"""
        return len(self.authorized_users)
    
    def get_active_users_count(self) -> int:
        """Get count of users with trading enabled"""
        return sum(1 for user_data in self.users.values() 
                  if user_data.get('trading_enabled', False))
    
    def get_setup_users_count(self) -> int:
        """Get count of users with complete setup"""
        return sum(1 for user_data in self.users.values() 
                  if user_data.get('setup_complete', False))
    
    def cleanup_inactive_users(self, days: int = 30) -> int:
        """
        Cleanup users inactive for specified days
        
        Args:
            days: Days of inactivity threshold
            
        Returns:
            Number of users cleaned up
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cleanup_count = 0
            
            inactive_users = []
            for user_id, user_data in self.users.items():
                last_active = user_data.get('last_active', user_data.get('created_at'))
                
                if last_active and last_active < cutoff_date:
                    # Don't cleanup users with active trades
                    if not user_data.get('is_active', False):
                        inactive_users.append(user_id)
            
            for user_id in inactive_users:
                # Backup before cleanup
                self.data_manager.backup_user_data(user_id)
                
                # Remove from memory and authorized users
                self.users.pop(user_id, None)
                self.authorized_users.discard(user_id)
                cleanup_count += 1
            
            if cleanup_count > 0:
                self.save_authorized_users()
                logger.info(f"Cleaned up {cleanup_count} inactive users")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error cleaning up inactive users: {e}")
            return 0