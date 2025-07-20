"""
Configuration settings for the Multi-Exchange Trading Bot
Updated with admin user configuration, Render cloud support, and API key management
Fixed path handling for logging
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7587490394:AAHYb4ZXMPy6cjelh0aeoVpGXJ2QFz4UmUA')

# Admin Configuration
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '5734898816'))
ADMIN_USER_IDS = [ADMIN_USER_ID, 541761607]  # Can add more admin IDs here

# Trading Configuration
SANDBOX_MODE = os.getenv('SANDBOX_MODE', 'False').lower() == 'true'
AUTHORIZATION_CODE = os.getenv('AUTHORIZATION_CODE', 'HYPE2025')

# API Keys Configuration (from environment variables)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')
BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_SECRET = os.getenv('BYBIT_SECRET')

# Auto-setup configuration
AUTO_SETUP_ADMIN_API = True  # Automatically setup API for admin users
DEFAULT_ADMIN_EXCHANGE = 'binance'  # Default exchange for admin auto-setup

# Balance Strategy Configuration
BALANCE_PERCENTAGE = float(os.getenv('BALANCE_PERCENTAGE', '0.002'))  # 0.2% of account balance
LEVERAGE = int(os.getenv('LEVERAGE', '25'))
TAKE_PROFIT_PCT = float(os.getenv('TAKE_PROFIT_PCT', '0.56'))  # 0.56% take profit

# Martingale Configuration
MARTINGALE_MULTIPLIER = float(os.getenv('MARTINGALE_MULTIPLIER', '1.35'))  # Each level is 35% more than previous
MARTINGALE_LEVELS = int(os.getenv('MARTINGALE_LEVELS', '11'))  # Maximum 11 levels
PRICE_DROP_TRIGGER = float(os.getenv('PRICE_DROP_TRIGGER', '1.1'))  # 1.1% price drop triggers next level

# Symbol Configuration
DEFAULT_SYMBOLS = {
    'binance': 'HYPE/USDT:USDT',
    'bybit': 'HYPE/USDT:USDT'  # Fixed: removed space
}

# Risk Management
MIN_BALANCE = float(os.getenv('MIN_BALANCE', '0.50'))  # Minimum $0.50 to start trading
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.3'))  # Maximum 30% of balance in one position

# Cloud Configuration for Render
PORT = int(os.getenv('PORT', 10000))  # Render provides PORT environment variable
IS_CLOUD_DEPLOYMENT = os.getenv('RENDER') is not None  # Detect if running on Render

# Path Configuration - Fixed for both local and cloud
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, os.getenv('DATA_DIR', 'data'))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Ensure directories exist (important for cloud deployment)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Data Storage
AUTHORIZED_USERS_FILE = 'authorized_users.pkl'
USER_DATA_PREFIX = 'user_'

# Logging Configuration - Fixed path handling
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'trading_bot.log'  # Just filename, logger will handle the path

# Cloud-specific settings
ENABLE_HEALTH_CHECK = IS_CLOUD_DEPLOYMENT  # Enable health check server for cloud
HEALTH_CHECK_INTERVAL = 300  # 5 minutes

# Exchange Specific Settings
EXCHANGE_SETTINGS = {
    'binance': {
        'rateLimit': 1200,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        }
    },
    'bybit': {
        'rateLimit': 1000,
        'enableRateLimit': True,
        'options': {
            'category': 'linear',
        }
    }
}

# Telegram Update Settings
TELEGRAM_TIMEOUT = int(os.getenv('TELEGRAM_TIMEOUT', '1'))
TELEGRAM_POLLING_INTERVAL = int(os.getenv('TELEGRAM_POLLING_INTERVAL', '1'))
MAIN_LOOP_INTERVAL = int(os.getenv('MAIN_LOOP_INTERVAL', '5'))

# Performance Tracking
TRACK_ANALYTICS = True
SAVE_TRADE_HISTORY = True
BACKUP_INTERVAL = int(os.getenv('BACKUP_INTERVAL', '3600'))  # Backup user data every hour

def get_martingale_sequence(base_amount: float) -> list:
    """
    Generate dynamic martingale sequence based on base amount
    Each level increases by MARTINGALE_MULTIPLIER
    """
    sequence = []
    current_amount = base_amount
    
    for i in range(MARTINGALE_LEVELS):
        sequence.append(round(current_amount, 4))
        current_amount *= MARTINGALE_MULTIPLIER
    
    return sequence

def calculate_base_amount(balance: float) -> float:
    """Calculate base trading amount as 0.2% of balance"""
    return round(balance * BALANCE_PERCENTAGE, 4)

def is_admin_user(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_USER_IDS

def has_admin_api_keys() -> bool:
    """Check if admin API keys are configured"""
    return bool(BINANCE_API_KEY and BINANCE_SECRET) or bool(BYBIT_API_KEY and BYBIT_SECRET)

def get_admin_api_config(exchange: str = None) -> dict:
    """Get API configuration for admin users"""
    if not exchange:
        exchange = DEFAULT_ADMIN_EXCHANGE
    
    if exchange == 'binance' and BINANCE_API_KEY and BINANCE_SECRET:
        return {
            'exchange': 'binance',
            'api_key': BINANCE_API_KEY,
            'secret': BINANCE_SECRET
        }
    elif exchange == 'bybit' and BYBIT_API_KEY and BYBIT_SECRET:
        return {
            'exchange': 'bybit',
            'api_key': BYBIT_API_KEY,
            'secret': BYBIT_SECRET
        }
    
    return None

def validate_settings():
    """Validate configuration settings"""
    errors = []
    
    if not TELEGRAM_TOKEN:
        errors.append("TELEGRAM_TOKEN is required")
    
    if BALANCE_PERCENTAGE <= 0 or BALANCE_PERCENTAGE > 0.1:
        errors.append("BALANCE_PERCENTAGE must be between 0 and 0.1 (10%)")
    
    if LEVERAGE < 1 or LEVERAGE > 100:
        errors.append("LEVERAGE must be between 1 and 100")
    
    if MARTINGALE_LEVELS < 3 or MARTINGALE_LEVELS > 20:
        errors.append("MARTINGALE_LEVELS must be between 3 and 20")
    
    if not ADMIN_USER_ID or ADMIN_USER_ID <= 0:
        errors.append("ADMIN_USER_ID must be a valid Telegram user ID")
    
    if errors:
        raise ValueError("Configuration errors: " + ", ".join(errors))
    
    return True

# Validate settings on import
validate_settings()

print(f"🔧 Configuration loaded")
print(f"📊 Balance Strategy: {BALANCE_PERCENTAGE*100}%")
print(f"👑 Admin User: {ADMIN_USER_ID}")
print(f"🌐 Mode: {'SANDBOX' if SANDBOX_MODE else 'LIVE'}")

# API Keys status
if has_admin_api_keys():
    print(f"🔑 Admin API Keys: Available")
    if BINANCE_API_KEY:
        print(f"🟡 Binance API: Configured")
    if BYBIT_API_KEY:
        print(f"🟠 Bybit API: Configured")
else:
    print(f"🔑 Admin API Keys: Not configured")

# Cloud deployment status
if IS_CLOUD_DEPLOYMENT:
    print(f"☁️ Render Cloud Deployment Detected")
    print(f"🌐 Port: {PORT}")
    print(f"📁 Data Directory: {DATA_DIR}")
    print(f"📝 Logs Directory: {LOGS_DIR}")
else:
    print(f"💻 Local Development Mode")
    print(f"📁 Data Directory: {DATA_DIR}")
    print(f"📝 Logs Directory: {LOGS_DIR}")
