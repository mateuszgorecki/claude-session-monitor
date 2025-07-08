#!/usr/bin/env python3
"""
Hook Log Compressor for Claude session monitor.
Provides compression capabilities for hook log files to prevent excessive growth.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from shared.constants import (
    HOOK_LOG_DIR, 
    HOOK_LOG_FILE_PATTERN,
    MAX_HOOK_LOG_ENTRIES,
    HOOK_LOG_COMPRESSION_THRESHOLD
)


class HookLogCompressor:
    """Manages compression of hook log files to prevent excessive size growth."""
    
    def __init__(self):
        """Initialize the hook log compressor."""
        self.logger = logging.getLogger(__name__)
        self.log_file_path = os.path.join(
            os.path.expanduser(HOOK_LOG_DIR), 
            HOOK_LOG_FILE_PATTERN
        )
    
    def should_compress(self) -> bool:
        """Check if the log file should be compressed based on entry count.
        
        Returns:
            True if compression is needed, False otherwise
        """
        if not os.path.exists(self.log_file_path):
            return False
        
        try:
            entry_count = self._count_log_entries()
            return entry_count >= HOOK_LOG_COMPRESSION_THRESHOLD
        except Exception as e:
            self.logger.error(f"Error checking if compression needed: {e}")
            return False
    
    def compress_log_file(self) -> bool:
        """Compress the hook log file by keeping only the most recent entries.
        
        Returns:
            True if compression was successful, False otherwise
        """
        if not os.path.exists(self.log_file_path):
            self.logger.debug("Hook log file does not exist, no compression needed")
            return True
        
        try:
            # Read all entries from the log file
            entries = self._read_log_entries()
            
            if len(entries) <= MAX_HOOK_LOG_ENTRIES:
                self.logger.debug(f"Log file has {len(entries)} entries, no compression needed")
                return True
            
            # Keep only the most recent entries
            recent_entries = entries[-MAX_HOOK_LOG_ENTRIES:]
            
            # Write compressed entries back to file
            self._write_log_entries(recent_entries)
            
            removed_count = len(entries) - len(recent_entries)
            self.logger.info(f"Compressed hook log file: removed {removed_count} old entries, kept {len(recent_entries)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to compress hook log file: {e}")
            return False
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get statistics about the current state of the log file.
        
        Returns:
            Dictionary containing compression statistics
        """
        stats = {
            'file_exists': os.path.exists(self.log_file_path),
            'entry_count': 0,
            'file_size_bytes': 0,
            'should_compress': False,
            'compression_threshold': HOOK_LOG_COMPRESSION_THRESHOLD,
            'max_entries_after_compression': MAX_HOOK_LOG_ENTRIES
        }
        
        if not stats['file_exists']:
            return stats
        
        try:
            stats['entry_count'] = self._count_log_entries()
            stats['file_size_bytes'] = os.path.getsize(self.log_file_path)
            stats['should_compress'] = stats['entry_count'] >= HOOK_LOG_COMPRESSION_THRESHOLD
        except Exception as e:
            self.logger.error(f"Error getting compression stats: {e}")
        
        return stats
    
    def _count_log_entries(self) -> int:
        """Count the number of entries in the log file.
        
        Returns:
            Number of entries in the log file
        """
        if not os.path.exists(self.log_file_path):
            return 0
        
        count = 0
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:  # Count non-empty lines
                        count += 1
        except Exception as e:
            self.logger.error(f"Error counting log entries: {e}")
            return 0
        
        return count
    
    def _read_log_entries(self) -> List[Dict[str, Any]]:
        """Read all entries from the log file.
        
        Returns:
            List of parsed JSON entries from the log file
        """
        entries = []
        
        if not os.path.exists(self.log_file_path):
            return entries
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
                        continue
        except Exception as e:
            self.logger.error(f"Error reading log entries: {e}")
        
        return entries
    
    def _write_log_entries(self, entries: List[Dict[str, Any]]) -> None:
        """Write entries to the log file.
        
        Args:
            entries: List of entries to write to the log file
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                for entry in entries:
                    json.dump(entry, f, separators=(',', ':'))
                    f.write('\n')
        except Exception as e:
            self.logger.error(f"Error writing log entries: {e}")
            raise
    
    def force_compress_to_size(self, target_entries: int) -> bool:
        """Force compression to a specific number of entries.
        
        Args:
            target_entries: Target number of entries to keep
            
        Returns:
            True if compression was successful, False otherwise
        """
        if target_entries <= 0:
            self.logger.error("Target entries must be positive")
            return False
        
        try:
            entries = self._read_log_entries()
            
            if len(entries) <= target_entries:
                self.logger.debug(f"Log file has {len(entries)} entries, target is {target_entries}, no compression needed")
                return True
            
            # Keep only the most recent entries
            recent_entries = entries[-target_entries:]
            
            # Write compressed entries back to file
            self._write_log_entries(recent_entries)
            
            removed_count = len(entries) - len(recent_entries)
            self.logger.info(f"Force compressed hook log file: removed {removed_count} old entries, kept {len(recent_entries)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to force compress hook log file: {e}")
            return False
    
    def clear_log_file(self) -> bool:
        """Clear the entire log file.
        
        Returns:
            True if clearing was successful, False otherwise
        """
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    pass  # Just open and close to truncate
                self.logger.info("Cleared hook log file completely")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear hook log file: {e}")
            return False