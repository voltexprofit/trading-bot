"""
Main bot class for the Multi-Exchange Trading Bot
"""

import json
import time
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from config.settings import (
    TELEGRAM_TIMEOUT, TELEGRAM_POLLING_INTERVAL, 
    MAIN_LOOP_INTERVAL, BACKUP_INTERVAL
)
from core.user_manager import UserManager
from core.exchanges import ExchangeManager
from core.trading import TradingEngine
from telegram.handlers import TelegramHandlers
from utils import setup_logger, log_error, log_user_action

logger = setup_logger('bot')

class MultiExchangeTradingBot:
    """
    Main trading bot class that coordinates all components
    """
    
    def __init__(self, telegram_token: str, sandbox: bool = True):
        """
        Initialize the trading bot
        
        Args:
            telegram_token: Telegram bot token
            sandbox: Whether to use sandbox mode
        """
        self.telegram_token = telegram_token
        self.telegram_url = f"https://api.telegram.org/bot{telegram_token}"
        self.sandbox = sandbox
        self.is_running = True
        self.last_update_id = 0
        self.last_backup_time = datetime.now()
        
        # Initialize components
        self.user_manager = UserManager()
        self.exchange_manager = ExchangeManager(sandbox)
        self.trading_engine = TradingEngine(self.exchange_manager)
        self.telegram_handlers = TelegramHandlers(
            self.user_manager, self.exchange_manager, self.trading_engine
        )
        
        logger.info(f"Multi-Exchange Trading Bot initialized - Sandbox: {sandbox}")
    
    def send_message(self, user_id: int, text: str, keyboard: Optional[Dict] = None) -> bool:
        """
        Send message to specific user
        
        Args:
            user_id: Telegram user ID
            text: Message text
            keyboard: Optional keyboard markup
            
        Returns:
            True if message sent successfully
        """
        try:
            url = f"{self.telegram_url}/sendMessage"
            
            data = {
                'chat_id': user_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            if keyboard:
                data['reply_markup'] = json.dumps(keyboard)
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.debug(f"Message sent to user {user_id}")
                return True
            else:
                logger.error(f"Failed to send message to user {user_id}: {response.text}")
                return False
                
        except Exception as e:
            log_error(logger, e, f"Error sending message to user {user_id}")
            return False
    
    def broadcast_message(self, text: str, keyboard: Optional[Dict] = None) -> int:
        """
        Send message to all authorized users
        
        Args:
            text: Message text
            keyboard: Optional keyboard markup
            
        Returns:
            Number of successful sends
        """
        success_count = 0
        
        for user_id in self.user_manager.authorized_users:
            if self.send_message(user_id, text, keyboard):
                success_count += 1
            time.sleep(0.1)  # Rate limiting
        
        logger.info(f"Broadcast sent to {success_count}/{len(self.user_manager.authorized_users)} users")
        return success_count
    
    def get_telegram_updates(self) -> bool:
        """
        Get updates from Telegram API
        
        Returns:
            True if updates retrieved successfully
        """
        try:
            url = f"{self.telegram_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': TELEGRAM_TIMEOUT
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['ok'] and data['result']:
                    for update in data['result']:
                        self.last_update_id = update['update_id']
                        
                        if 'message' in update:
                            self.handle_telegram_message(update['message'])
                
                return True
            else:
                logger.error(f"Telegram API error: {response.text}")
                return False
                
        except Exception as e:
            log_error(logger, e, "Error getting Telegram updates")
            return False
    
    def handle_telegram_message(self, message: Dict[str, Any]):
        """
        Handle incoming Telegram message
        
        Args:
            message: Telegram message object
        """
        try:
            user_id = message['from']['id']
            
            # Process message through handlers
            response = self.telegram_handlers.handle_message(message)
            
            # Send response
            self.send_message(user_id, response['text'], response.get('keyboard'))
            
        except Exception as e:
            log_error(logger, e, "Error handling Telegram message")
            
            # Send error message to user if possible
            try:
                user_id = message['from']['id']
                self.send_message(user_id, "❌ An error occurred. Please try again.")
            except:
                pass
    
    def telegram_polling_loop(self):
        """Background thread for Telegram polling"""
        logger.info("Starting Telegram polling loop...")
        
        while self.is_running:
            try:
                self.get_telegram_updates()
                time.sleep(TELEGRAM_POLLING_INTERVAL)
                
            except Exception as e:
                log_error(logger, e, "Error in Telegram polling loop")
                time.sleep(5)
    
    def trading_loop(self):
        """Background thread for trading operations"""
        logger.info("Starting trading loop...")
        
        while self.is_running:
            try:
                # Process trading for each authorized user
                for user_id in list(self.user_manager.authorized_users):
                    if user_id in self.user_manager.users:
                        user_data = self.user_manager.users[user_id]
                        
                        try:
                            # Process user's trading logic
                            success = self.trading_engine.process_user_trading(user_id, user_data)
                            
                            if success:
                                # Save user data after successful processing
                                self.user_manager.save_user_data(user_id)
                            
                        except Exception as e:
                            log_error(logger, e, f"Error processing trading for user {user_id}")
                
                time.sleep(MAIN_LOOP_INTERVAL)
                
            except Exception as e:
                log_error(logger, e, "Error in trading loop")
                time.sleep(10)
    
    def maintenance_loop(self):
        """Background thread for maintenance tasks"""
        logger.info("Starting maintenance loop...")
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Backup data periodically
                if (current_time - self.last_backup_time).seconds > BACKUP_INTERVAL:
                    self.perform_backup()
                    self.last_backup_time = current_time
                
                # Cleanup old data
                self.user_manager.data_manager.cleanup_old_backups(days_to_keep=7)
                
                time.sleep(3600)  # Run maintenance every hour
                
            except Exception as e:
                log_error(logger, e, "Error in maintenance loop")
                time.sleep(600)  # Wait 10 minutes on error
    
    def perform_backup(self):
        """Perform data backup"""
        try:
            # Backup authorized users
            self.user_manager.save_authorized_users()
            
            # Backup individual user data
            backup_count = 0
            for user_id in self.user_manager.authorized_users:
                if self.user_manager.data_manager.backup_user_data(user_id):
                    backup_count += 1
            
            logger.info(f"Backup completed for {backup_count} users")
            
        except Exception as e:
            log_error(logger, e, "Error performing backup")
    
    def send_trading_notification(self, user_id: int, notification_type: str, **kwargs):
        """
        Send trading notification to user
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            **kwargs: Additional data
        """
        try:
            if user_id not in self.user_manager.users:
                return
            
            user_data = self.user_manager.users[user_id]
            
            # Create notification message
            message = self.telegram_handlers.create_trading_update_message(
                user_id, user_data, notification_type, **kwargs
            )
            
            # Send notification
            self.send_message(user_id, message)
            
        except Exception as e:
            log_error(logger, e, f"Error sending notification to user {user_id}")
    
    def emergency_stop_all(self) -> int:
        """
        Emergency stop for all users
        
        Returns:
            Number of users stopped
        """
        stopped_count = 0
        
        for user_id in self.user_manager.authorized_users:
            if user_id in self.user_manager.users:
                user_data = self.user_manager.users[user_id]
                
                try:
                    if user_data.get('is_active'):
                        success = self.trading_engine.emergency_close_position(user_id, user_data)
                        if success:
                            stopped_count += 1
                            self.send_message(user_id, "🚨 EMERGENCY STOP - All positions closed by admin")
                    else:
                        user_data['trading_enabled'] = False
                        stopped_count += 1
                        self.send_message(user_id, "🚨 EMERGENCY STOP - Trading disabled by admin")
                    
                    self.user_manager.save_user_data(user_id)
                    
                except Exception as e:
                    log_error(logger, e, f"Error emergency stopping user {user_id}")
        
        logger.info(f"Emergency stop completed for {stopped_count} users")
        return stopped_count
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            stats = {
                'bot_info': {
                    'running': self.is_running,
                    'sandbox_mode': self.sandbox,
                    'uptime': datetime.now(),
                    'last_backup': self.last_backup_time
                },
                'users': {
                    'total_authorized': self.user_manager.get_authorized_users_count(),
                    'setup_complete': self.user_manager.get_setup_users_count(),
                    'trading_active': self.user_manager.get_active_users_count()
                },
                'storage': self.user_manager.data_manager.get_storage_stats()
            }
            
            return stats
            
        except Exception as e:
            log_error(logger, e, "Error getting system stats")
            return {}
    
    def run(self):
        """Main bot execution"""
        try:
            logger.info("🚀 Starting Multi-Exchange Trading Bot...")
            
            # Start background threads
            telegram_thread = threading.Thread(target=self.telegram_polling_loop, daemon=True)
            trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
            maintenance_thread = threading.Thread(target=self.maintenance_loop, daemon=True)
            
            telegram_thread.start()
            trading_thread.start()
            maintenance_thread.start()
            
            # Send startup notification
            if self.user_manager.authorized_users:
                startup_msg = f"🤖 MULTI-EXCHANGE BOT v2.0 STARTED!\n"
                startup_msg += f"====================================\n\n"
                startup_msg += f"👥 {len(self.user_manager.authorized_users)} users connected\n"
                startup_msg += f"🏢 Binance & Bybit support\n"
                startup_msg += f"💰 Dynamic 0.2% balance strategy\n"
                startup_msg += f"🌐 {'SANDBOX' if self.sandbox else 'LIVE'} trading mode\n"
                startup_msg += f"✅ All personal bots ready!\n\n"
                startup_msg += f"Use 📊 Status to check your bot state."
                
                self.broadcast_message(startup_msg)
            
            logger.info("✅ Bot started successfully - All systems operational")
            
            # Main loop - keep bot alive
            try:
                while self.is_running:
                    time.sleep(10)
                    
                    # Health check
                    if not telegram_thread.is_alive():
                        logger.error("Telegram thread died - restarting...")
                        telegram_thread = threading.Thread(target=self.telegram_polling_loop, daemon=True)
                        telegram_thread.start()
                    
                    if not trading_thread.is_alive():
                        logger.error("Trading thread died - restarting...")
                        trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
                        trading_thread.start()
                    
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                self.shutdown()
                
        except Exception as e:
            log_error(logger, e, "Fatal error in bot execution")
            self.shutdown()
    
    def shutdown(self):
        """Graceful bot shutdown"""
        try:
            logger.info("🛑 Shutting down bot...")
            
            self.is_running = False
            
            # Perform final backup
            self.perform_backup()
            
            # Send shutdown notification
            if self.user_manager.authorized_users:
                shutdown_msg = "🛑 Multi-Exchange Bot is shutting down.\n"
                shutdown_msg += "All data has been saved.\n"
                shutdown_msg += "Bot will restart shortly."
                
                self.broadcast_message(shutdown_msg)
            
            logger.info("✅ Bot shutdown completed")
            
        except Exception as e:
            log_error(logger, e, "Error during bot shutdown")