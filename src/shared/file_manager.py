#!/usr/bin/env python3
"""
File manager with atomic write operations and iCloud Drive synchronization.
Provides safe file operations for daemon/client architecture.
"""
import json
import os
import tempfile
import shutil
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class FileManager:
    """Manages file operations with atomic writes and iCloud sync."""
    
    def __init__(self, file_path: str, icloud_sync_path: Optional[str] = None):
        """
        Initialize FileManager.
        
        Args:
            file_path: Path to the main data file
            icloud_sync_path: Optional path to iCloud Drive sync file
        """
        self.file_path = file_path
        self.icloud_sync_path = icloud_sync_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    def write_data(self, data: Dict[str, Any]) -> bool:
        """
        Write data to file using atomic operation.
        
        Args:
            data: Dictionary to write as JSON
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create temporary file in same directory as target
            temp_dir = os.path.dirname(self.file_path)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=temp_dir,
                prefix='.tmp_',
                suffix='.json'
            )
            
            try:
                # Write data to temporary file
                with os.fdopen(temp_fd, 'w') as temp_file:
                    json.dump(data, temp_file, indent=2, ensure_ascii=False)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                
                # Set appropriate permissions (owner read/write only)
                os.chmod(temp_path, 0o600)
                
                # Atomic move (rename) temporary file to target
                shutil.move(temp_path, self.file_path)
                
                # Sync to iCloud if configured
                if self.icloud_sync_path:
                    self._sync_to_icloud(data)
                
                return True
                
            except Exception as e:
                # Clean up temporary file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to write data to {self.file_path}: {e}")
            return False
    
    def read_data(self) -> Dict[str, Any]:
        """
        Read data from file.
        
        Returns:
            Dictionary with file contents, or empty dict if file doesn't exist or is corrupted
        """
        try:
            if not os.path.exists(self.file_path):
                return {}
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                return data
                
        except (json.JSONDecodeError, OSError, IOError) as e:
            self.logger.error(f"Failed to read data from {self.file_path}: {e}")
            return {}
    
    def _sync_to_icloud(self, data: Dict[str, Any]) -> bool:
        """
        Sync data to iCloud Drive.
        
        Args:
            data: Dictionary to sync
            
        Returns:
            True if successful, False otherwise
        """
        if not self.icloud_sync_path:
            return False
        
        try:
            # Ensure iCloud directory exists
            icloud_dir = os.path.dirname(self.icloud_sync_path)
            os.makedirs(icloud_dir, exist_ok=True)
            
            # Create temporary file for atomic iCloud write
            temp_fd, temp_path = tempfile.mkstemp(
                dir=icloud_dir,
                prefix='.tmp_icloud_',
                suffix='.json'
            )
            
            try:
                # Write data to temporary file
                with os.fdopen(temp_fd, 'w') as temp_file:
                    json.dump(data, temp_file, indent=2, ensure_ascii=False)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                
                # Set appropriate permissions
                os.chmod(temp_path, 0o644)  # More permissive for iCloud
                
                # Atomic move to iCloud location
                shutil.move(temp_path, self.icloud_sync_path)
                
                self.logger.debug(f"Successfully synced data to iCloud: {self.icloud_sync_path}")
                return True
                
            except Exception as e:
                # Clean up temporary file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise e
                
        except Exception as e:
            self.logger.warning(f"Failed to sync to iCloud {self.icloud_sync_path}: {e}")
            # iCloud sync failure shouldn't prevent main operation
            return False
    
    def file_exists(self) -> bool:
        """Check if the main file exists."""
        return os.path.exists(self.file_path)
    
    def get_file_size(self) -> int:
        """Get file size in bytes, or 0 if file doesn't exist."""
        try:
            return os.path.getsize(self.file_path)
        except OSError:
            return 0
    
    def get_file_mtime(self) -> float:
        """Get file modification time, or 0 if file doesn't exist."""
        try:
            return os.path.getmtime(self.file_path)
        except OSError:
            return 0.0
    
    def backup_file(self, backup_suffix: str = '.bak') -> bool:
        """
        Create a backup of the current file.
        
        Args:
            backup_suffix: Suffix for backup file
            
        Returns:
            True if backup created successfully, False otherwise
        """
        if not self.file_exists():
            return False
        
        backup_path = self.file_path + backup_suffix
        
        try:
            shutil.copy2(self.file_path, backup_path)
            self.logger.debug(f"Created backup: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create backup {backup_path}: {e}")
            return False
    
    def cleanup_old_backups(self, max_backups: int = 5) -> None:
        """
        Remove old backup files, keeping only the most recent ones.
        
        Args:
            max_backups: Maximum number of backup files to keep
        """
        try:
            backup_dir = os.path.dirname(self.file_path)
            base_name = os.path.basename(self.file_path)
            
            # Find all backup files
            backup_files = []
            for file in os.listdir(backup_dir):
                if file.startswith(base_name) and file.endswith('.bak'):
                    backup_path = os.path.join(backup_dir, file)
                    backup_files.append((backup_path, os.path.getmtime(backup_path)))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old backups
            for backup_path, _ in backup_files[max_backups:]:
                try:
                    os.unlink(backup_path)
                    self.logger.debug(f"Removed old backup: {backup_path}")
                except OSError as e:
                    self.logger.warning(f"Failed to remove backup {backup_path}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")


class ConfigFileManager(FileManager):
    """Specialized FileManager for configuration files."""
    
    def __init__(self, config_dir: str = "~/.config/claude-monitor"):
        """
        Initialize config file manager.
        
        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = os.path.expanduser(config_dir)
        config_file = os.path.join(self.config_dir, "config.json")
        
        # iCloud path for config sync
        icloud_config_path = os.path.expanduser(
            "~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/config.json"
        )
        
        super().__init__(config_file, icloud_config_path)
    
    def load_config_with_defaults(self, defaults: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load configuration with fallback to defaults.
        
        Args:
            defaults: Default configuration values
            
        Returns:
            Configuration dictionary
        """
        config = self.read_data()
        
        # Merge with defaults
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        
        return config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration with validation.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if saved successfully, False otherwise
        """
        # Create backup before saving
        self.backup_file()
        
        # Save new configuration
        success = self.write_data(config)
        
        if success:
            # Cleanup old backups
            self.cleanup_old_backups()
        
        return success


class DataFileManager(FileManager):
    """Specialized FileManager for monitoring data files."""
    
    def __init__(self, data_dir: str = "~/.config/claude-monitor"):
        """
        Initialize data file manager.
        
        Args:
            data_dir: Data directory path
        """
        self.data_dir = os.path.expanduser(data_dir)
        data_file = os.path.join(self.data_dir, "monitor_data.json")
        
        # iCloud path for data sync (for widget access)
        icloud_data_path = os.path.expanduser(
            "~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/monitor_data.json"
        )
        
        super().__init__(data_file, icloud_data_path)
    
    def write_monitoring_data(self, monitoring_data: Dict[str, Any]) -> bool:
        """
        Write monitoring data with timestamp.
        
        Args:
            monitoring_data: Monitoring data dictionary
            
        Returns:
            True if written successfully, False otherwise
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        # Add timestamp
        monitoring_data['last_file_update'] = datetime.now(ZoneInfo("UTC")).isoformat()
        
        return self.write_data(monitoring_data)