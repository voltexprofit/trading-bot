"""
Robust logging utilities for the Multi-Exchange Trading Bot
Fixed console errors and improved cloud compatibility
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that gracefully handles bad file descriptors"""
    
    def emit(self, record):
        try:
            super().emit(record)
        except (OSError, ValueError):
            # Silently ignore bad file descriptor errors
            pass
    
    def flush(self):
        try:
            if self.stream and hasattr(self.stream, 'flush'):
                self.stream.flush()
        except (OSError, ValueError):
            # Silently ignore flush errors
            pass

class RobustFileHandler(logging.FileHandler):
    """File handler that creates directories and handles errors gracefully"""
    
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        # Ensure directory exists
        log_dir = os.path.dirname(filename)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError:
                pass
        
        super().__init__(filename, mode, encoding, delay)
    
    def emit(self, record):
        try:
            super().emit(record)
        except (OSError, IOError):
            # If file logging fails, try to create a backup console message
            try:
                print(f"LOG: {self.format(record)}")
            except:
                pass

def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Setup a robust logger with improved error handling
    
    Args:
        name: Logger name
        level: Log level (default from settings)
    
    Returns:
        Configured logger instance
    """
    # Import here to avoid circular imports
    try:
        from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, IS_CLOUD_DEPLOYMENT
        if level is None:
            level = LOG_LEVEL
    except ImportError:
        level = level or 'INFO'
        LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        LOG_FILE = 'trading_bot.log'
        IS_CLOUD_DEPLOYMENT = os.getenv('RENDER') is not None
    
    logger = logging.getLogger(name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatters
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Console handler - robust version
    try:
        console_handler = SafeStreamHandler(sys.stdout)
        
        # In cloud deployment, reduce console verbosity
        if IS_CLOUD_DEPLOYMENT:
            console_handler.setLevel(logging.WARNING)  # Only warnings and errors
        else:
            console_handler.setLevel(logging.INFO)
            
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    except Exception as e:
        # If console handler fails, continue without it
        print(f"Warning: Could not set up console logging: {e}")
    
    # File handler - robust version
    try:
        # Ensure logs directory exists
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        
        # Handle LOG_FILE path correctly
        if os.path.isabs(LOG_FILE):
            log_path = LOG_FILE
        else:
            log_path = os.path.join(logs_dir, LOG_FILE)
        
        # Use rotating file handler for better management
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Only log success message if not in cloud mode to reduce noise
        if not IS_CLOUD_DEPLOYMENT:
            logger.info(f"Logger '{name}' initialized - Log file: {log_path}")
        
    except Exception as e:
        # If file logging fails, continue with console only
        if not IS_CLOUD_DEPLOYMENT:
            print(f"Warning: Could not set up file logging: {e}")
            print("Continuing with console logging only")
    
    return logger

def log_trade(logger: logging.Logger, user_id: int, action: str, **kwargs):
    """
    Log trading actions with robust error handling
    
    Args:
        logger: Logger instance
        user_id: User ID
        action: Trading action
        **kwargs: Additional trade data
    """
    trade_data = {
        'user_id': user_id,
        'action': action,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"TRADE: {trade_data}"
    
    # Try multiple logging methods
    try:
        logger.info(message)
    except Exception:
        try:
            # Fallback to direct file write
            with open('logs/trades.log', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - {message}\n")
        except Exception:
            try:
                # Final fallback to console
                print(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
            except Exception:
                pass  # Give up gracefully

def log_user_action(logger: logging.Logger, user_id: int, action: str, **kwargs):
    """
    Log user actions with robust error handling
    
    Args:
        logger: Logger instance
        user_id: User ID
        action: User action
        **kwargs: Additional action data
    """
    action_data = {
        'user_id': user_id,
        'action': action,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"USER_ACTION: {action_data}"
    
    try:
        logger.info(message)
    except Exception:
        try:
            # Fallback to console
            print(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        except Exception:
            pass  # Give up gracefully

def log_error(logger: logging.Logger, error: Exception, context: str = None, **kwargs):
    """
    Log errors with robust error handling
    
    Args:
        logger: Logger instance
        error: Exception instance
        context: Error context description
        **kwargs: Additional error data
    """
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }
    
    message = f"ERROR: {error_data}"
    
    try:
        logger.error(message)
    except Exception:
        try:
            # Fallback to direct file write
            with open('logs/errors.log', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - {message}\n")
        except Exception:
            try:
                # Final fallback to console
                print(f"ERROR: {datetime.now().strftime('%H:%M:%S')} - {message}")
            except Exception:
                pass  # Give up gracefully

def get_cloud_logger(name: str = 'trading_bot_cloud'):
    """
    Get a logger optimized for cloud deployment
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Cloud-optimized formatter (more compact)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    # Console handler for cloud (minimal output)
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)  # Only important messages
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for cloud
    try:
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/cloud_bot.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass  # Continue without file logging if it fails
    
    return logger

def setup_cloud_logging():
    """Setup logging optimized for cloud deployment"""
    try:
        from config.settings import IS_CLOUD_DEPLOYMENT
        
        if IS_CLOUD_DEPLOYMENT:
            return get_cloud_logger()
        else:
            return setup_logger()
            
    except ImportError:
        return setup_logger()

# Disable default logging for some noisy libraries
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

# Main logger instance
_main_logger = None

def get_main_logger():
    """Get or create the main logger instance"""
    global _main_logger
    if _main_logger is None:
        _main_logger = setup_logger('trading_bot')
    return _main_logger

# Export commonly used functions
__all__ = [
    'setup_logger',
    'log_trade',
    'log_user_action',
    'log_error',
    'get_cloud_logger',
    'setup_cloud_logging',
    'get_main_logger'
]