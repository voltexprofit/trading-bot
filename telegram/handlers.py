"""
Telegram message handlers for the Multi-Exchange Trading Bot
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from config.settings import AUTHORIZATION_CODE
from utils import setup_logger, log_user_action, format_currency, format_percentage
from telegram.keyboards import (
    get_keyboard_for_user_state, format_keyboard_markup,
    get_trading_control_keyboard, get_analytics_keyboard,
    get_confirmation_keyboard
)

logger = setup_logger('handlers')

class TelegramHandlers:
    """Handles all Telegram message processing"""
    
    def __init__(self, user_manager, exchange_manager, trading_engine):
        self.user_manager = user_manager
        self.exchange_manager = exchange_manager
        self.trading_engine = trading_engine
    
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main message handler that routes to specific handlers
        
        Args:
            message: Telegram message object
            
        Returns:
            Response dictionary with text and keyboard
        """
        try:
            user_id = message['from']['id']
            text = message.get('text', '')
            username = message['from'].get('username', '')
            first_name = message['from'].get('first_name', '')
            
            logger.info(f"Message from user {user_id} ({username}): {text}")
            
            # Update user info if authorized
            if self.user_manager.is_authorized(user_id):
                self.user_manager.update_user_info(user_id, username, first_name)
            
            # Handle authorization commands
            if text.startswith('/authorize'):
                return self._handle_authorization(user_id, text, username, first_name)
            
            # Check if user is authorized
            if not self.user_manager.is_authorized(user_id):
                return {
                    'text': "❌ You are not authorized to use this bot.\n\nTo get access, use:\n/authorize HYPE2025",
                    'keyboard': None
                }
            
            # Route to specific handlers
            return self._route_message(user_id, text)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {
                'text': "❌ An error occurred processing your message. Please try again.",
                'keyboard': None
            }
    
    def _route_message(self, user_id: int, text: str) -> Dict[str, Any]:
        """Route message to appropriate handler"""
        user_data = self.user_manager.get_user_data(user_id)
        
        # Command handlers
        if text.startswith('/'):
            return self._handle_commands(user_id, text, user_data)
        
        # Button handlers
        if text in ['🟡 Binance', '🟠 Bybit']:
            return self._handle_exchange_selection(user_id, text, user_data)
        elif text == '📊 Status':
            return self._handle_status(user_id, user_data)
        elif text == '💰 Balance':
            return self._handle_balance(user_id, user_data)
        elif text in ['🚀 Start Trading', '🚀 Start']:
            return self._handle_start_trading(user_id, user_data)
        elif text == '📈 Position':
            return self._handle_position(user_id, user_data)
        elif text == '📈 Analytics':
            return self._handle_analytics(user_id, user_data)
        elif text == '📊 Performance':
            return self._handle_performance(user_id, user_data)
        elif text == '🛑 Safe Stop':
            return self._handle_safe_stop(user_id, user_data)
        elif text == '🚨 Emergency':
            return self._handle_emergency(user_id, user_data)
        elif text == '⚙️ Settings':
            return self._handle_settings(user_id, user_data)
        elif text == '👥 Users':
            return self._handle_users_list(user_id, user_data)
        elif text == '❓ Help':
            return self._handle_help(user_id, user_data)
        else:
            return self._handle_default(user_id, user_data)
    
    def _handle_commands(self, user_id: int, text: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle slash commands"""
        if text.startswith('/setapi'):
            return self._handle_api_setup(user_id, text, user_data)
        elif text in ['/status', '/start']:
            return self._handle_status(user_id, user_data)
        elif text == '/balance':
            return self._handle_balance(user_id, user_data)
        elif text == '/help':
            return self._handle_help(user_id, user_data)
        else:
            return self._handle_default(user_id, user_data)
    
    def _handle_authorization(self, user_id: int, text: str, username: str, first_name: str) -> Dict[str, Any]:
        """Handle user authorization"""
        parts = text.split(' ')
        if len(parts) > 1:
            auth_code = parts[1]
            success, message = self.user_manager.authorize_user(user_id, username, first_name, auth_code)
            
            if success:
                user_data = self.user_manager.get_user_data(user_id)
                keyboard = get_keyboard_for_user_state(user_data, user_id)
                return {
                    'text': message,
                    'keyboard': format_keyboard_markup(keyboard)
                }
            else:
                return {
                    'text': message,
                    'keyboard': None
                }
        else:
            return {
                'text': f"Please use: /authorize {AUTHORIZATION_CODE}",
                'keyboard': None
            }
    
    def _handle_exchange_selection(self, user_id: int, text: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle exchange selection"""
        exchange_type = 'binance' if '🟡' in text else 'bybit'
        success, message = self.user_manager.select_exchange(user_id, exchange_type)
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_api_setup(self, user_id: int, text: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API key setup"""
        if not user_data.get('exchange_selected'):
            return {
                'text': "❌ Please select an exchange first (🟡 Binance or 🟠 Bybit)",
                'keyboard': format_keyboard_markup(get_keyboard_for_user_state(user_data))
            }
        
        parts = text.split(' ')
        if len(parts) != 3:
            return {
                'text': "Usage: /setapi YOUR_API_KEY YOUR_SECRET",
                'keyboard': None
            }
        
        exchange_type = user_data['exchange_type']
        api_key = parts[1]
        secret = parts[2]
        
        exchange_name = "Binance" if exchange_type == 'binance' else "Bybit"
        emoji = "🟡" if exchange_type == 'binance' else "🟠"
        
        # Create exchange instance
        success, result = self.exchange_manager.create_exchange_instance(exchange_type, api_key, secret)
        
        if success:
            # Save exchange instance and update user data
            user_data['exchange'] = result
            user_data['api_key'] = api_key
            user_data['secret'] = secret
            user_data['setup_complete'] = True
            
            # Get balance and update strategy
            balance = self.exchange_manager.get_balance(result, exchange_type)
            self.user_manager.update_user_balance_strategy(user_id, balance)
            self.user_manager.save_user_data(user_id)
            
            message = f"✅ {emoji} {exchange_name} Setup Successful!\n\n"
            message += f"💰 Your Balance: {format_currency(balance)} USDT\n"
            message += f"🎯 Symbol: {user_data['symbol']}\n"
            message += f"📊 Base Amount: {format_currency(user_data['base_amount'])} (0.2% of balance)\n"
            message += f"🚀 Ready to start trading!\n\n"
            message += f"Click 🚀 Start Trading to begin auto-trading."
            
        else:
            message = f"❌ {emoji} {exchange_name} Setup Failed!\n\n"
            message += f"Error: {result}\n\n"
            message += f"Please check:\n"
            message += f"• API key is correct\n"
            message += f"• Secret is correct\n"
            message += f"• API has required permissions\n"
            message += f"• API is activated in {exchange_name}"
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_status(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request"""
        if not user_data.get('setup_complete'):
            return {
                'text': "❌ Please complete setup first. Use ⚙️ Settings",
                'keyboard': format_keyboard_markup(get_keyboard_for_user_state(user_data))
            }
        
        status = self.trading_engine.get_user_trading_status(user_id, user_data)
        
        exchange_name = "Binance" if user_data['exchange_type'] == 'binance' else "Bybit"
        emoji = "🟡" if user_data['exchange_type'] == 'binance' else "🟠"
        
        message = f"🤖 YOUR BOT STATUS\n"
        message += f"==================\n\n"
        message += f"Exchange: {emoji} {exchange_name}\n"
        message += f"Balance: {format_currency(status['current_balance'])} USDT\n"
        message += f"HYPE Price: {format_currency(status['current_price'], decimals=3)}\n"
        message += f"Trading: {'🟢 ENABLED - AUTO CYCLING' if status['trading_enabled'] else '🔴 DISABLED'}\n"
        message += f"Active Position: {'🟢 Yes' if status['is_active'] else '🔴 No'}\n\n"
        
        message += f"📊 YOUR STATS:\n"
        message += f"Total Trades: {status['total_trades']}\n"
        message += f"Completed Cycles: {status['cycle_count']}\n"
        message += f"Base Amount: {format_currency(user_data.get('base_amount', 0))} (0.2%)\n"
        
        if user_data.get('starting_balance'):
            roi = ((status['current_balance'] - user_data['starting_balance']) / user_data['starting_balance'] * 100)
            message += f"ROI: {format_percentage(roi)}\n"
        
        keyboard = get_trading_control_keyboard(status['is_active'], status['trading_enabled'])
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_balance(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle balance request"""
        if not user_data.get('setup_complete'):
            return {
                'text': "❌ Please complete setup first. Use ⚙️ Settings",
                'keyboard': format_keyboard_markup(get_keyboard_for_user_state(user_data))
            }
        
        status = self.trading_engine.get_user_trading_status(user_id, user_data)
        total_risk = sum(user_data.get('martingale_sequence', []))
        
        exchange_name = "Binance" if user_data['exchange_type'] == 'binance' else "Bybit"
        emoji = "🟡" if user_data['exchange_type'] == 'binance' else "🟠"
        
        message = f"💰 YOUR BALANCE\n"
        message += f"===============\n\n"
        message += f"Exchange: {emoji} {exchange_name}\n"
        message += f"Current: {format_currency(status['current_balance'])} USDT\n"
        
        if user_data.get('starting_balance'):
            growth = status['current_balance'] - user_data['starting_balance']
            roi = (growth / user_data['starting_balance'] * 100) if user_data['starting_balance'] > 0 else 0
            message += f"Starting: {format_currency(user_data['starting_balance'])} USDT\n"
            message += f"Growth: {format_currency(growth)} USDT\n"
            message += f"ROI: {format_percentage(roi)}\n\n"
        
        message += f"📊 DYNAMIC STRATEGY (0.2%):\n"
        message += f"Base Amount: {format_currency(user_data.get('base_amount', 0))} USDT\n"
        message += f"Total Risk: {format_currency(total_risk)} USDT\n"
        
        if total_risk > 0:
            safety_ratio = status['current_balance'] / total_risk
            message += f"Safety Ratio: {safety_ratio:.1f}x\n"
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_start_trading(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start trading request"""
        if not user_data.get('setup_complete'):
            return {
                'text': "❌ Please complete setup first. Use ⚙️ Settings",
                'keyboard': format_keyboard_markup(get_keyboard_for_user_state(user_data))
            }
        
        # Validate user for trading
        is_valid, error_msg = self.trading_engine.validate_user_for_trading(user_data)
        if not is_valid:
            return {
                'text': f"❌ Cannot start trading: {error_msg}",
                'keyboard': format_keyboard_markup(get_keyboard_for_user_state(user_data))
            }
        
        # Enable trading
        user_data['trading_enabled'] = True
        user_data['start_button_pressed'] = True
        user_data['safe_stop_requested'] = False
        self.user_manager.save_user_data(user_id)
        
        status = self.trading_engine.get_user_trading_status(user_id, user_data)
        exchange_name = "Binance" if user_data['exchange_type'] == 'binance' else "Bybit"
        emoji = "🟡" if user_data['exchange_type'] == 'binance' else "🟠"
        
        message = f"✅ YOUR TRADING ENABLED!\n"
        message += f"========================\n\n"
        message += f"Exchange: {emoji} {exchange_name}\n"
        message += f"Balance: {format_currency(status['current_balance'])} USDT\n"
        message += f"Base Amount: {format_currency(user_data.get('base_amount', 0))} USDT\n"
        message += f"Strategy: Dynamic 0.2% Balance\n"
        message += f"🚀 Starting auto-cycling...\n\n"
        message += f"📊 Your personal bot is now active!"
        
        log_user_action(logger, user_id, 'trading_started', 
                       exchange=user_data['exchange_type'], 
                       balance=status['current_balance'])
        
        keyboard = get_trading_control_keyboard(False, True)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_position(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle position request"""
        if not user_data.get('is_active'):
            return {
                'text': "📈 No active position",
                'keyboard': format_keyboard_markup(get_keyboard_for_user_state(user_data))
            }
        
        status = self.trading_engine.get_user_trading_status(user_id, user_data)
        exchange_name = "Binance" if user_data['exchange_type'] == 'binance' else "Bybit"
        emoji = "🟡" if user_data['exchange_type'] == 'binance' else "🟠"
        
        message = f"📈 YOUR CURRENT POSITION\n"
        message += f"========================\n\n"
        message += f"Exchange: {emoji} {exchange_name}\n"
        message += f"Entry: {format_currency(user_data.get('entry_price', 0), decimals=3)}\n"
        message += f"Current: {format_currency(status['current_price'], decimals=3)}\n"
        message += f"Avg Entry: {format_currency(status.get('weighted_avg_entry', 0), decimals=3)}\n"
        message += f"Levels: {len(user_data.get('position_levels', []))}\n"
        message += f"Step: {status.get('current_step', 0) + 1}/{status.get('max_steps', 0)}\n\n"
        
        # Show profit/loss
        if status.get('weighted_avg_entry'):
            profit_pct = ((status['current_price'] - status['weighted_avg_entry']) / status['weighted_avg_entry'] * 100)
            margin_return = profit_pct * user_data.get('leverage', 25)
            message += f"Price P&L: {format_percentage(profit_pct)}\n"
            message += f"Margin P&L: {format_percentage(margin_return)}\n"
        
        keyboard = get_trading_control_keyboard(True, True)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_safe_stop(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle safe stop request"""
        user_data['safe_stop_requested'] = True
        user_data['trading_enabled'] = False
        self.user_manager.save_user_data(user_id)
        
        log_user_action(logger, user_id, 'safe_stop_requested')
        
        message = "🛑 SAFE STOP ACTIVATED\n"
        message += "=====================\n\n"
        
        if user_data.get('is_active'):
            message += "Your current position will be closed when:\n"
            message += "• Take profit target is reached, OR\n"
            message += "• Current cycle completes\n\n"
            message += "No new cycles will start.\n"
            message += "Monitor your position for completion."
        else:
            message += "✅ Safe stop completed!\n"
            message += "No active position to close.\n"
            message += "Trading has been disabled."
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_emergency(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency stop request"""
        if user_data.get('is_active'):
            # Close position immediately
            success = self.trading_engine.emergency_close_position(user_id, user_data)
            
            if success:
                message = "🚨 EMERGENCY STOP COMPLETED!\n"
                message += "============================\n\n"
                message += "✅ All positions closed immediately\n"
                message += "✅ Trading disabled\n"
                message += "✅ Bot stopped safely\n\n"
                message += "Check your exchange for final balance."
            else:
                message = "❌ EMERGENCY STOP FAILED!\n"
                message += "=========================\n\n"
                message += "Could not close positions automatically.\n"
                message += "Please check your exchange manually!\n\n"
                message += "Trading has been disabled."
        else:
            user_data['trading_enabled'] = False
            message = "🚨 EMERGENCY STOP ACTIVATED!\n"
            message += "============================\n\n"
            message += "✅ Trading disabled\n"
            message += "✅ No active positions to close\n"
            message += "✅ Bot stopped safely"
        
        self.user_manager.save_user_data(user_id)
        log_user_action(logger, user_id, 'emergency_stop')
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_analytics(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics request"""
        return {
            'text': "📈 Analytics feature coming soon!\n\nStay tuned for detailed performance metrics.",
            'keyboard': format_keyboard_markup(get_analytics_keyboard())
        }
    
    def _handle_performance(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle performance request"""
        return {
            'text': "📊 Performance metrics coming soon!\n\nDetailed reports will be available soon.",
            'keyboard': format_keyboard_markup(get_keyboard_for_user_state(user_data))
        }
    
    def _handle_settings(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle settings request"""
        if not user_data.get('exchange_selected'):
            setup_msg = f"⚙️ BOT SETUP\n"
            setup_msg += f"============\n\n"
            setup_msg += f"🎯 STEP 1: Choose Exchange\n"
            setup_msg += f"Click 🟡 Binance or 🟠 Bybit\n\n"
        
        elif not user_data.get('setup_complete'):
            exchange_name = "Binance" if user_data['exchange_type'] == 'binance' else "Bybit"
            emoji = "🟡" if user_data['exchange_type'] == 'binance' else "🟠"
            
            setup_msg = f"⚙️ BOT SETUP\n"
            setup_msg += f"============\n\n"
            setup_msg += f"✅ Exchange: {emoji} {exchange_name}\n"
            setup_msg += f"❌ API Setup Required\n\n"
            setup_msg += f"🎯 STEP 2: Setup API Keys\n"
            setup_msg += f"Command: /setapi YOUR_API_KEY YOUR_SECRET\n\n"
            
            if user_data['exchange_type'] == 'binance':
                setup_msg += f"📋 Binance Requirements:\n"
                setup_msg += f"• Enable Futures Trading\n"
                setup_msg += f"• Enable Spot & Margin Trading\n"
            else:
                setup_msg += f"📋 Bybit Requirements:\n"
                setup_msg += f"• Enable Derivatives Trading\n"
                setup_msg += f"• Enable Wallet/Account Read\n"
        
        else:
            exchange_name = "Binance" if user_data['exchange_type'] == 'binance' else "Bybit"
            emoji = "🟡" if user_data['exchange_type'] == 'binance' else "🟠"
            status = self.trading_engine.get_user_trading_status(user_id, user_data)
            
            setup_msg = f"⚙️ YOUR SETTINGS\n"
            setup_msg += f"================\n\n"
            setup_msg += f"✅ Setup Complete!\n"
            setup_msg += f"📊 Exchange: {emoji} {exchange_name}\n"
            setup_msg += f"💰 Balance: {format_currency(status['current_balance'])} USDT\n"
            setup_msg += f"🎯 Symbol: {user_data['symbol']}\n"
            setup_msg += f"📊 Total Trades: {user_data.get('total_trades', 0)}\n"
            setup_msg += f"🔄 Total Cycles: {user_data.get('cycle_count', 0)}\n\n"
            setup_msg += f"📊 STRATEGY SETTINGS:\n"
            setup_msg += f"Base Amount: {format_currency(user_data.get('base_amount', 0))} (0.2%)\n"
            setup_msg += f"Leverage: {user_data.get('leverage', 25)}x\n"
            setup_msg += f"Take Profit: {user_data.get('take_profit_pct', 0.56)}%\n\n"
            setup_msg += f"🔧 To change API: /setapi NEW_KEY NEW_SECRET\n"
            setup_msg += f"🚀 Ready to trade!"
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': setup_msg,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_users_list(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle users list request"""
        users_msg = f"👥 ACTIVE USERS\n"
        users_msg += f"===============\n\n"
        users_msg += f"Total Users: {self.user_manager.get_authorized_users_count()}\n"
        users_msg += f"Setup Complete: {self.user_manager.get_setup_users_count()}\n"
        users_msg += f"Trading Active: {self.user_manager.get_active_users_count()}\n\n"
        
        # Show limited user info for privacy
        count = 0
        for uid in list(self.user_manager.authorized_users)[:10]:  # Show max 10 users
            if uid in self.user_manager.users:
                count += 1
                user_info = self.user_manager.users[uid]
                name = user_info.get('first_name', 'Unknown')
                status = "🟢 Active" if user_info.get('trading_enabled') else "⚪ Idle"
                setup = "✅" if user_info.get('setup_complete') else "❌"
                
                exchange = ""
                if user_info.get('exchange_type'):
                    if user_info['exchange_type'] == 'binance':
                        exchange = "🟡 BIN"
                    else:
                        exchange = "🟠 BYB"
                
                users_msg += f"{count}. {name} | {exchange} | {setup} | {status}\n"
        
        if len(self.user_manager.authorized_users) > 10:
            users_msg += f"\n... and {len(self.user_manager.authorized_users) - 10} more users"
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': users_msg,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_help(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help request"""
        help_msg = f"❓ HELP & COMMANDS\n"
        help_msg += f"==================\n\n"
        help_msg += f"🔰 GETTING STARTED:\n"
        help_msg += f"/authorize HYPE2025 - Get bot access\n"
        help_msg += f"🟡 Binance or 🟠 Bybit - Choose exchange\n"
        help_msg += f"/setapi KEY SECRET - Setup trading\n"
        help_msg += f"🚀 Start Trading - Begin auto-trading\n\n"
        
        help_msg += f"📊 MONITORING:\n"
        help_msg += f"📊 Status - Bot status & position\n"
        help_msg += f"💰 Balance - Account balance\n"
        help_msg += f"📈 Position - Current trades\n"
        help_msg += f"📈 Analytics - Trading statistics\n\n"
        
        help_msg += f"🛑 CONTROLS:\n"
        help_msg += f"🛑 Safe Stop - Stop after current cycle\n"
        help_msg += f"🚨 Emergency - Immediate stop & close\n"
        help_msg += f"⚙️ Settings - Configuration options\n\n"
        
        help_msg += f"💡 STRATEGY INFO:\n"
        help_msg += f"• Uses 0.2% of balance as base amount\n"
        help_msg += f"• Dynamic martingale sequence\n"
        help_msg += f"• Automatic balance adjustment\n"
        help_msg += f"• 25x leverage, 0.56% take profit\n\n"
        
        help_msg += f"🏢 SUPPORTED EXCHANGES:\n"
        help_msg += f"🟡 Binance Futures\n"
        help_msg += f"🟠 Bybit Derivatives\n\n"
        
        help_msg += f"💬 Need help? Check ⚙️ Settings!"
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': help_msg,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def _handle_default(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown messages"""
        message = "Use the buttons below to control your bot!"
        
        if not user_data.get('setup_complete'):
            message = "Please complete setup first. Use ⚙️ Settings or select an exchange."
        elif not user_data.get('trading_enabled'):
            message = "Use 🚀 Start Trading to begin, or check 📊 Status for your bot state."
        
        keyboard = get_keyboard_for_user_state(user_data, user_id)
        return {
            'text': message,
            'keyboard': format_keyboard_markup(keyboard)
        }
    
    def create_trading_update_message(self, user_id: int, user_data: Dict[str, Any], 
                                    update_type: str, **kwargs) -> str:
        """Create formatted trading update messages"""
        exchange_name = "Binance" if user_data['exchange_type'] == 'binance' else "Bybit"
        emoji = "🟡" if user_data['exchange_type'] == 'binance' else "🟠"
        
        if update_type == 'cycle_started':
            msg = f"🚀 Cycle #{user_data.get('cycle_count', 0) + 1} Started!\n"
            msg += f"{emoji} {exchange_name}\n"
            msg += f"BUY {kwargs.get('amount', 0)} HYPE at {format_currency(kwargs.get('price', 0), decimals=3)}\n"
            msg += f"Step: 1/{len(user_data.get('martingale_sequence', []))}\n"
            msg += f"Margin: {format_currency(kwargs.get('margin', 0))}\n"
            msg += f"📊 Trade #{user_data.get('total_trades', 0)}"
            
        elif update_type == 'martingale_added':
            level = kwargs.get('level', 1)
            msg = f"📈 Martingale Level {level}\n"
            msg += f"{emoji} {exchange_name}\n"
            msg += f"Added: {kwargs.get('amount', 0)} HYPE at {format_currency(kwargs.get('price', 0), decimals=3)}\n"
            msg += f"Step: {level}/{len(user_data.get('martingale_sequence', []))}\n"
            msg += f"💔 1.1% drop triggered level\n"
            
            # Calculate new average
            from utils.calculations import calculate_weighted_average_entry
            weighted_avg = calculate_weighted_average_entry(user_data.get('position_levels', []))
            if weighted_avg:
                msg += f"🎯 New Avg Entry: {format_currency(weighted_avg, decimals=3)}\n"
            msg += f"📊 Trade #{user_data.get('total_trades', 0)}"
            
        elif update_type == 'cycle_completed':
            profit_pct = kwargs.get('profit_pct', 0)
            profit_usd = kwargs.get('profit_usd', 0)
            margin_return = profit_pct * user_data.get('leverage', 25)
            
            msg = f"💰 CYCLE #{user_data.get('cycle_count', 0)} COMPLETE!\n"
            msg += f"{emoji} {exchange_name}\n"
            msg += f"📈 Margin Return: +{format_percentage(margin_return)}\n"
            msg += f"💵 Profit: {format_currency(profit_usd)}\n"
            msg += f"📊 Contracts Closed: {kwargs.get('amount', 0)}\n"
            msg += f"📊 Total Trades: {user_data.get('total_trades', 0)}\n"
            msg += f"🔄 Starting new cycle in 30 seconds..."
            
        elif update_type == 'balance_updated':
            old_balance = kwargs.get('old_balance', 0)
            new_balance = kwargs.get('new_balance', 0)
            old_base = kwargs.get('old_base', 0)
            new_base = kwargs.get('new_base', 0)
            
            msg = f"💰 BALANCE STRATEGY UPDATED\n"
            msg += f"{emoji} {exchange_name}\n"
            msg += f"Balance: {format_currency(old_balance)} → {format_currency(new_balance)}\n"
            msg += f"Base (0.2%): {format_currency(old_base)} → {format_currency(new_base)}\n"
            msg += f"✅ Martingale sequence recalculated"
            
        else:
            msg = f"📊 {update_type.replace('_', ' ').title()}\n{emoji} {exchange_name}"
        
        return msg