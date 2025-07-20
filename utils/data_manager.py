"""
Data persistence utilities for the Multi-Exchange Trading Bot
"""

import os
import pickle
import json
from datetime import datetime
from typing import Dict, Any, Set, Optional
from pathlib import Path

from config.settings import DATA_DIR, AUTHORIZED_USERS_FILE, USER_DATA_PREFIX
from utils.logger import setup_logger

logger = setup_logger('data_manager')

class DataManager:
    """Handles all data persistence operations"""
    
    def __init__(self):
        self.data_dir = Path(DATA_DIR)
        self.data_dir.mkdir(exist_ok=True)
        
        self.authorized_users_path = self.data_dir / AUTHORIZED_USERS_FILE
        
    def save_authorized_users(self, authorized_users: Set[int]) -> bool:
        """
        Save authorized users set to file
        
        Args:
            authorized_users: Set of authorized user IDs
            
        Returns:
            True if successful
        """
        try:
            with open(self.authorized_users_path, 'wb') as f:
                pickle.dump(authorized_users, f)
            logger.info(f"Saved {len(authorized_users)} authorized users")
            return True
        except Exception as e:
            logger.error(f"Error saving authorized users: {e}")
            return False
    
    def load_authorized_users(self) -> Set[int]:
        """
        Load authorized users set from file
        
        Returns:
            Set of authorized user IDs
        """
        try:
            if self.authorized_users_path.exists():
                with open(self.authorized_users_path, 'rb') as f:
                    authorized_users = pickle.load(f)
                logger.info(f"Loaded {len(authorized_users)} authorized users")
                return authorized_users
        except Exception as e:
            logger.error(f"Error loading authorized users: {e}")
        
        return set()
    
    def save_user_data(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """
        Save user data to file
        
        Args:
            user_id: User ID
            user_data: User data dictionary
            
        Returns:
            True if successful
        """
        try:
            user_file = self.data_dir / f"{USER_DATA_PREFIX}{user_id}_data.pkl"
            
            # Add timestamp to user data
            user_data['last_saved'] = datetime.now()
            
            with open(user_file, 'wb') as f:
                pickle.dump(user_data, f)
            
            logger.debug(f"Saved data for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving data for user {user_id}: {e}")
            return False
    
    def load_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Load user data from file
        
        Args:
            user_id: User ID
            
        Returns:
            User data dictionary or None if not found
        """
        try:
            user_file = self.data_dir / f"{USER_DATA_PREFIX}{user_id}_data.pkl"
            
            if user_file.exists():
                with open(user_file, 'rb') as f:
                    user_data = pickle.load(f)
                logger.debug(f"Loaded data for user {user_id}")
                return user_data
        except Exception as e:
            logger.error(f"Error loading data for user {user_id}: {e}")
        
        return None
    
    def backup_user_data(self, user_id: int) -> bool:
        """
        Create backup of user data
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        try:
            user_file = self.data_dir / f"{USER_DATA_PREFIX}{user_id}_data.pkl"
            
            if user_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.data_dir / f"{USER_DATA_PREFIX}{user_id}_backup_{timestamp}.pkl"
                
                # Copy the file
                import shutil
                shutil.copy2(user_file, backup_file)
                
                logger.info(f"Created backup for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error creating backup for user {user_id}: {e}")
        
        return False
    
    def export_user_data_json(self, user_id: int) -> Optional[str]:
        """
        Export user data to JSON format
        
        Args:
            user_id: User ID
            
        Returns:
            JSON string or None if failed
        """
        try:
            user_data = self.load_user_data(user_id)
            if user_data:
                # Convert datetime objects to strings
                def convert_datetime(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                json_data = json.dumps(user_data, default=convert_datetime, indent=2)
                
                # Save to file
                json_file = self.data_dir / f"{USER_DATA_PREFIX}{user_id}_export.json"
                with open(json_file, 'w') as f:
                    f.write(json_data)
                
                logger.info(f"Exported data for user {user_id} to JSON")
                return json_data
        except Exception as e:
            logger.error(f"Error exporting data for user {user_id}: {e}")
        
        return None
    
    def get_all_user_ids(self) -> list[int]:
        """
        Get list of all user IDs with saved data
        
        Returns:
            List of user IDs
        """
        user_ids = []
        
        try:
            for file_path in self.data_dir.glob(f"{USER_DATA_PREFIX}*_data.pkl"):
                # Extract user ID from filename
                filename = file_path.name
                user_id_str = filename.replace(USER_DATA_PREFIX, '').replace('_data.pkl', '')
                
                try:
                    user_id = int(user_id_str)
                    user_ids.append(user_id)
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting user IDs: {e}")
        
        return sorted(user_ids)
    
    def cleanup_old_backups(self, days_to_keep: int = 7) -> int:
        """
        Cleanup backup files older than specified days
        
        Args:
            days_to_keep: Number of days to keep backups
            
        Returns:
            Number of files cleaned up
        """
        try:
            from datetime import timedelta
            
            cleanup_count = 0
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            for file_path in self.data_dir.glob(f"{USER_DATA_PREFIX}*_backup_*.pkl"):
                # Get file modification time
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if mod_time < cutoff_time:
                    file_path.unlink()
                    cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} old backup files")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            total_files = 0
            total_size = 0
            user_count = 0
            backup_count = 0
            
            for file_path in self.data_dir.iterdir():
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
                    
                    if file_path.name.endswith('_data.pkl'):
                        user_count += 1
                    elif '_backup_' in file_path.name:
                        backup_count += 1
            
            return {
                'total_files': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'user_data_files': user_count,
                'backup_files': backup_count,
                'data_directory': str(self.data_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}