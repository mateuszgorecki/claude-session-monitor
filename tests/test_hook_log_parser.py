#!/usr/bin/env python3
"""
Tests for HookLogParser class.
Tests parsing of hook log entries and conversion to ActivitySessionData.
"""

import unittest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, mock_open
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from daemon.hook_log_parser import HookLogParser
from shared.data_models import ActivitySessionData, ActivitySessionStatus


class TestHookLogParser(unittest.TestCase):
    """Test cases for HookLogParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = HookLogParser()
    
    def test_parse_valid_notification_log_line(self):
        """Test parsing a valid notification log line."""
        log_line = json.dumps({
            "timestamp": "2025-07-06T10:30:00+00:00",
            "project_name": "test-project",
            "session_id": "session_123",
            "event_type": "notification",
            "data": {
                "message": "Task completed",
                "title": "Claude Code",
                "transcript_path": "/path/to/transcript"
            }
        })
        
        result = self.parser.parse_log_line(log_line)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['session_id'], "session_123")
        self.assertEqual(result['event_type'], "notification")
        self.assertIn('timestamp', result)
    
    def test_parse_valid_stop_log_line(self):
        """Test parsing a valid stop log line."""
        log_line = json.dumps({
            "timestamp": "2025-07-06T10:35:00+00:00",
            "project_name": "test-project",
            "session_id": "session_123",
            "event_type": "stop",
            "data": {
                "reason": "user_requested",
                "duration_seconds": 300
            }
        })
        
        result = self.parser.parse_log_line(log_line)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['session_id'], "session_123")
        self.assertEqual(result['event_type'], "stop")
    
    def test_parse_invalid_json_line(self):
        """Test parsing an invalid JSON line returns None."""
        invalid_log_line = "This is not valid JSON"
        
        result = self.parser.parse_log_line(invalid_log_line)
        
        self.assertIsNone(result)
    
    def test_parse_missing_required_fields(self):
        """Test parsing JSON with missing required fields returns None."""
        incomplete_log_line = json.dumps({
            "timestamp": "2025-07-06T10:30:00+00:00",
            # Missing session_id and event_type
            "data": {}
        })
        
        result = self.parser.parse_log_line(incomplete_log_line)
        
        self.assertIsNone(result)
    
    def test_create_activity_session_from_notification_event(self):
        """Test creating ActivitySessionData from notification event."""
        event_data = {
            "timestamp": "2025-07-06T10:30:00+00:00",
            "project_name": "test-project",
            "session_id": "session_123",
            "event_type": "notification",
            "data": {"message": "Task completed"}
        }
        
        session = self.parser.create_activity_session(event_data)
        
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, "session_123")
        self.assertEqual(session.status, ActivitySessionStatus.ACTIVE.value)
        self.assertIsInstance(session.start_time, datetime)
    
    def test_create_activity_session_from_stop_event(self):
        """Test creating ActivitySessionData from stop event."""
        event_data = {
            "timestamp": "2025-07-06T10:35:00+00:00",
            "project_name": "test-project",
            "session_id": "session_123",
            "event_type": "stop",
            "data": {"reason": "completed"}
        }
        
        session = self.parser.create_activity_session(event_data)
        
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, "session_123")
        self.assertEqual(session.status, ActivitySessionStatus.STOPPED.value)
        self.assertIsNotNone(session.end_time)
    
    def test_parse_log_file_returns_activity_sessions(self):
        """Test parsing a complete log file and returning ActivitySessionData list."""
        sample_log_content = '''{"timestamp": "2025-07-06T10:30:00+00:00", "project_name": "project-1", "session_id": "session_123", "event_type": "notification", "data": {}}
{"timestamp": "2025-07-06T10:35:00+00:00", "project_name": "project-1", "session_id": "session_123", "event_type": "stop", "data": {}}
{"timestamp": "2025-07-06T10:40:00+00:00", "project_name": "project-2", "session_id": "session_456", "event_type": "notification", "data": {}}'''
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=len(sample_log_content)), \
             patch('builtins.open', mock_open(read_data=sample_log_content)):
            sessions = self.parser.parse_log_file("/fake/path/to/log.txt")
        
        self.assertEqual(len(sessions), 3)
        self.assertIsInstance(sessions[0], ActivitySessionData)
        self.assertEqual(sessions[0].session_id, "session_123")
        self.assertEqual(sessions[1].status, ActivitySessionStatus.STOPPED.value)
    
    def test_parse_log_file_handles_corrupted_lines(self):
        """Test parsing log file with some corrupted lines."""
        sample_log_content = '''{"timestamp": "2025-07-06T10:30:00+00:00", "project_name": "project-1", "session_id": "session_123", "event_type": "notification", "data": {}}
CORRUPTED LINE - NOT JSON
{"timestamp": "2025-07-06T10:40:00+00:00", "project_name": "project-2", "session_id": "session_456", "event_type": "notification", "data": {}}
{"incomplete": "json"'''
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=len(sample_log_content)), \
             patch('builtins.open', mock_open(read_data=sample_log_content)):
            sessions = self.parser.parse_log_file("/fake/path/to/log.txt")
        
        # Should return only valid sessions, ignoring corrupted lines
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0].session_id, "session_123")
        self.assertEqual(sessions[1].session_id, "session_456")


if __name__ == '__main__':
    unittest.main()