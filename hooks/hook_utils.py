import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Any


class HookLogger:
    """Thread-safe logger for Claude Code hook events.
    
    Provides atomic file operations for logging hook events in JSON format.
    Each log entry includes a UTC timestamp and the provided event data.
    """
    
    def __init__(self, log_file_path: str):
        """Initialize the hook logger.
        
        Args:
            log_file_path: Path to the log file where events will be written
        """
        self.log_file_path = log_file_path
        self._lock = threading.Lock()
    
    def log_event(self, event_data: Dict[str, Any]) -> None:
        """Log an event to the log file in JSON format.
        
        Thread-safe method that appends the event data to the log file.
        Automatically creates the directory if it doesn't exist.
        
        Args:
            event_data: Dictionary containing event information
        """
        # Add timestamp to event data (using timezone-aware datetime)
        event_with_timestamp = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **event_data
        }
        
        # Ensure directory exists
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Thread-safe file writing
        with self._lock:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                json.dump(event_with_timestamp, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')