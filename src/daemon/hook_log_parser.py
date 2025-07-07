#!/usr/bin/env python3
"""
Hook Log Parser for Claude session monitor.
Parses log files created by Claude Code hooks and converts them to ActivitySessionData.
"""

import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from shared.data_models import ActivitySessionData, ActivitySessionStatus


class HookLogParser:
    """Parser for hook log files created by Claude Code hooks.
    
    This class handles parsing of JSON log files created by Claude Code hooks
    and converts them into ActivitySessionData objects for integration with
    the session monitoring system.
    """
    
    def __init__(self):
        """Initialize the hook log parser."""
        self.logger = logging.getLogger(__name__)
    
    def parse_log_line(self, log_line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line from hook log file.
        
        Args:
            log_line: JSON string representing a log entry
            
        Returns:
            Parsed log entry as dictionary, or None if invalid
        """
        if not log_line or not log_line.strip():
            return None
            
        try:
            data = json.loads(log_line.strip())
            
            # Validate required fields
            required_fields = ['timestamp', 'session_id', 'event_type', 'project_name']
            if not all(key in data for key in required_fields):
                self.logger.warning(f"Log line missing required fields {required_fields}: {log_line[:100]}...")
                return None
            
            # Validate field types
            if not isinstance(data['session_id'], str) or not data['session_id'].strip():
                self.logger.warning(f"Invalid session_id in log line: {log_line[:100]}...")
                return None
                
            if not isinstance(data['event_type'], str) or not data['event_type'].strip():
                self.logger.warning(f"Invalid event_type in log line: {log_line[:100]}...")
                return None
                
            return data
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON log line: {e}, line: {log_line[:100]}...")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing log line: {e}, line: {log_line[:100]}...")
            return None
    
    def create_activity_session(self, event_data: Dict[str, Any]) -> Optional[ActivitySessionData]:
        """Create ActivitySessionData from parsed event data.
        
        Args:
            event_data: Parsed event data from log line
            
        Returns:
            ActivitySessionData object or None if invalid
        """
        try:
            session_id = event_data['session_id']
            event_type = event_data['event_type']
            timestamp_str = event_data['timestamp']
            
            # Parse timestamp with multiple format support
            timestamp = self._parse_timestamp(timestamp_str)
            if timestamp is None:
                self.logger.warning(f"Invalid timestamp format: {timestamp_str}")
                return None
            
            # Determine status and end_time based on event type
            if event_type.lower() in ['stop', 'subagentstop']:
                status = ActivitySessionStatus.STOPPED.value
                end_time = timestamp
                # For stop events, set start_time slightly before end_time to satisfy validation
                start_time = timestamp - timedelta(microseconds=1)
            elif event_type.lower() in ['notification', 'activity']:
                status = ActivitySessionStatus.ACTIVE.value
                end_time = None
                start_time = timestamp
            else:
                # Unknown event type, log warning but default to active
                self.logger.warning(f"Unknown event type '{event_type}', defaulting to ACTIVE")
                status = ActivitySessionStatus.ACTIVE.value
                end_time = None
                start_time = timestamp
            
            # Extract metadata from event data
            metadata = event_data.get('data', {})
            if not isinstance(metadata, dict):
                metadata = {}
            
            session = ActivitySessionData(
                project_name=event_data['project_name'],
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                status=status,
                event_type=event_type,
                metadata=metadata
            )
            
            # Validate the created session
            try:
                session.validate_schema()
            except Exception as e:
                self.logger.warning(f"Created session failed validation: {e}")
                return None
            
            return session
            
        except (KeyError, ValueError, TypeError) as e:
            self.logger.warning(f"Failed to create activity session: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating activity session: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string with multiple format support.
        
        Args:
            timestamp_str: Timestamp string to parse
            
        Returns:
            Parsed datetime object or None if invalid
        """
        if not timestamp_str:
            return None
            
        try:
            # Handle different timestamp formats
            # 1. ISO format with Z timezone
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            
            # 2. ISO format parsing
            return datetime.fromisoformat(timestamp_str)
            
        except ValueError:
            try:
                # 3. Alternative parsing for different formats
                return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
    
    def parse_log_file(self, file_path: str) -> List[ActivitySessionData]:
        """Parse a complete log file and return list of ActivitySessionData.
        
        Args:
            file_path: Path to the log file
            
        Returns:
            List of ActivitySessionData objects
        """
        sessions = []
        
        if not file_path or not os.path.exists(file_path):
            self.logger.debug(f"Log file does not exist: {file_path}")
            return sessions
        
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                self.logger.debug(f"Log file is empty: {file_path}")
                return sessions
            
            self.logger.debug(f"Parsing log file: {file_path} (size: {file_size} bytes)")
            
            parsed_lines = 0
            valid_sessions = 0
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parsed_lines += 1
                    
                    # Parse the log line
                    event_data = self.parse_log_line(line)
                    if event_data is None:
                        continue
                    
                    # Create activity session
                    session = self.create_activity_session(event_data)
                    if session is not None:
                        sessions.append(session)
                        valid_sessions += 1
            
            self.logger.info(f"Parsed {parsed_lines} lines from {file_path}, created {valid_sessions} valid sessions")
                        
        except FileNotFoundError:
            self.logger.debug(f"Log file not found: {file_path}")
        except PermissionError:
            self.logger.warning(f"Permission denied reading log file: {file_path}")
        except IOError as e:
            self.logger.error(f"IO error reading log file {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing log file {file_path}: {e}")
        
        return sessions