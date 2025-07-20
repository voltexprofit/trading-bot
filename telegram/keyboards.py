"""
Telegram keyboard layouts for the Multi-Exchange Trading Bot
Updated with admin functionality
"""

from typing import List, Dict, Any, Optional
from config.settings import is_admin_user

def get_welcome_keyboard() -> List[List[Dict[str, str]]]:
    """Keyboard for new/unauthorized users"""
    return [
        [{'text': '🚀 Start Using Bot'}],
        [{'text': '❓ Help'}, {'text': '📋 Instructions'}]
    ]

def get_exchange_selection_keyboard() -> List[List[Dict[str, str]]]:
    """Keyboard for exchange selection"""
    return [
        [{'text': '🟡 Binance'}, {'text': '🟠 Bybit'}],
        [{'text': '❓ Help'}, {'text': '⚙️ Setup'}]
    ]

def get_setup_keyboard() -> List[List[Dict[str, str]]]:
    """Keyboard for API setup"""
    return [
        [{'text': '🔑 Setup API Keys'}],
        [{'text': '📋 API Instructions'}, {'text': '❓ Help'}],
        [{'text': '🔙 Change Exchange'}]
    ]

def get_main_keyboard() -> List[List[Dict[str, str]]]:
    """Main keyboard for fully setup users"""
    return [
        [{'text': '📊 Status'}, {'text': '💰 Balance'}],
        [{'text': '🚀 Start Trading'}, {'text': '📈 Position'}],
        [{'text': '📈 Analytics'}, {'text': '📊 Performance'}],
        [{'text': '🛑 Safe Stop'}, {'text': '🚨 Emergency'}],
        [{'text': '⚙️ Settings'}, {'text': '👥 Users'}]
    ]

def get_admin_keyboard() -> List[List[Dict[str, str]]]:
    """Extended keyboard for admin users"""
    return [
        [{'text': '📊 Status'}, {'text': '💰 Balance'}],
        [{'text': '🚀 Start Trading'}, {'text': '📈 Position'}],
        [{'text': '📈 Analytics'}, {'text': '📊 Performance'}],
        [{'text': '🛑 Safe Stop'}, {'text': '🚨 Emergency'}],
        [{'text': '⚙️ Settings'}, {'text': '👥 Users'}],
        [{'text': '🔧 Admin Panel'}, {'text': '📊 System Stats'}],
        [{'text': '🚨 Emergency All'}, {'text': '💾 Backup All'}]
    ]

def get_admin_panel_keyboard() -> List[List[Dict[str, str]]]:
    """Admin panel keyboard"""
    return [
        [{'text': '👥 User Management'}, {'text': '📊 System Stats'}],
        [{'text': '🔧 Bot Settings'}, {'text': '📝 View Logs'}],
        [{'text': '💾 Backup Data'}, {'text': '🧹 Cleanup'}],
        [{'text': '🚨 Emergency All'}, {'text': '⏸️ Pause All'}],
        [{'text': '📈 Performance'}, {'text': '🔄 Restart Bot'}],
        [{'text': '🔙 Back to Main'}]
    ]

def get_user_management_keyboard() -> List[List[Dict[str, str]]]:
    """User management keyboard (admin only)"""
    return [
        [{'text': '👥 List All Users'}, {'text': '🔍 User Search'}],
        [{'text': '➕ Add User'}, {'text': '❌ Remove User'}],
        [{'text': '📊 User Stats'}, {'text': '🔧 User Settings'}],
        [{'text': '💾 Backup Users'}, {'text': '🧹 Cleanup Inactive'}],
        [{'text': '🔙 Back to Admin'}]
    ]

def get_system_controls_keyboard() -> List[List[Dict[str, str]]]:
    """System controls keyboard (admin only)"""
    return [
        [{'text': '⏸️ Pause All Trading'}, {'text': '▶️ Resume All Trading'}],
        [{'text': '🚨 Emergency Stop All'}, {'text': '🔄 Restart Bot'}],
        [{'text': '📊 System Health'}, {'text': '💾 Force Backup'}],
        [{'text': '🧹 Cleanup Data'}, {'text': '📊 Performance Report'}],
        [{'text': '🔙 Back to Admin'}]
    ]

def get_analytics_keyboard() -> List[List[Dict[str, str]]]:
    """Keyboard for analytics options"""
    return [
        [{'text': '💹 ROI Stats'}, {'text': '📈 Returns'}],
        [{'text': '📊 Trade History'}, {'text': '📉 Performance'}],
        [{'text': '🔄 Cycles'}, {'text': '💰 Profit/Loss'}],
        [{'text': '🔙 Back to Main'}]
    ]

def get_settings_keyboard() -> List[List[Dict[str, str]]]:
    """Keyboard for settings options"""
    return [
        [{'text': '🔧 Trading Settings'}, {'text': '🔑 API Settings'}],
        [{'text': '📊 Risk Management'}, {'text': '⚙️ Exchange'}],
        [{'text': '💾 Export Data'}, {'text': '🗑️ Reset Data'}],
        [{'text': '🔙 Back to Main'}]
    ]

def get_confirmation_keyboard(action: str) -> List[List[Dict[str, str]]]:
    """Keyboard for confirmation dialogs"""
    return [
        [{'text': f'✅ Confirm {action}'}, {'text': '❌ Cancel'}],
        [{'text': '🔙 Back'}]
    ]

def get_trading_control_keyboard(is_active: bool, trading_enabled: bool) -> List[List[Dict[str, str]]]:
    """Dynamic keyboard based on trading state"""
    keyboard = []
    
    if not trading_enabled:
        keyboard.extend([
            [{'text': '🚀 Start Trading'}],
            [{'text': '📊 Status'}, {'text': '💰 Balance'}]
        ])
    elif is_active:
        keyboard.extend([
            [{'text': '📈 Position'}, {'text': '📊 Status'}],
            [{'text': '🛑 Safe Stop'}, {'text': '🚨 Emergency'}]
        ])
    else:
        keyboard.extend([
            [{'text': '📊 Status'}, {'text': '💰 Balance'}],
            [{'text': '🛑 Safe Stop'}, {'text': '⚙️ Settings'}]
        ])
    
    # Always include help and analytics
    keyboard.extend([
        [{'text': '📈 Analytics'}, {'text': '❓ Help'}]
    ])
    
    return keyboard

def get_keyboard_for_user_state(user_data: Dict[str, Any], user_id: int = None) -> List[List[Dict[str, str]]]:
    """
    Get appropriate keyboard based on user state
    
    Args:
        user_data: User data dictionary
        user_id: User ID (for admin check)
        
    Returns:
        Keyboard layout
    """
    # Check if user is authorized
    if not user_data.get('authorized', False):
        return get_welcome_keyboard()
    
    # Check if exchange is selected
    if not user_data.get('exchange_selected', False):
        return get_exchange_selection_keyboard()
    
    # Check if setup is complete
    if not user_data.get('setup_complete', False):
        return get_setup_keyboard()
    
    # Check if this is an admin user
    if user_id and is_admin_user(user_id):
        return get_admin_keyboard()
    
    # Return main keyboard for fully setup users
    return get_main_keyboard()

def format_keyboard_markup(keyboard: List[List[Dict[str, str]]]) -> Dict[str, Any]:
    """
    Format keyboard for Telegram API
    
    Args:
        keyboard: Keyboard layout
        
    Returns:
        Formatted reply markup
    """
    return {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': False,
        'selective': False
    }

def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
    """
    Create inline keyboard markup
    
    Args:
        buttons: Inline button layout
        
    Returns:
        Formatted inline keyboard markup
    """
    return {
        'inline_keyboard': buttons
    }

def get_quick_start_keyboard() -> List[List[Dict[str, str]]]:
    """Quick start keyboard for new users"""
    return [
        [{'text': '🟡 Quick Setup Binance'}, {'text': '🟠 Quick Setup Bybit'}],
        [{'text': '📋 Full Setup Guide'}, {'text': '❓ Need Help?'}],
        [{'text': '👑 Admin Login'}]  # Special admin option
    ]

def get_balance_strategy_info_keyboard() -> List[List[Dict[str, str]]]:
    """Keyboard showing balance strategy information"""
    return [
        [{'text': '📊 How 0.2% Works'}, {'text': '💡 Strategy Benefits'}],
        [{'text': '⚖️ Risk Management'}, {'text': '📈 Examples'}],
        [{'text': '🔧 Adjust Settings'}, {'text': '🔙 Back'}]
    ]

def keyboard_from_user_state(user_data: Optional[Dict[str, Any]], 
                           user_id: Optional[int] = None) -> List[List[Dict[str, str]]]:
    """
    Get the most appropriate keyboard for user's current state
    
    Args:
        user_data: User data dictionary (can be None)
        user_id: User ID for admin checks
        
    Returns:
        Appropriate keyboard layout
    """
    if not user_data:
        # Special case for admin user
        if user_id and is_admin_user(user_id):
            return get_quick_start_keyboard()
        return get_welcome_keyboard()
    
    return get_keyboard_for_user_state(user_data, user_id)