#!/usr/bin/env python3
"""
Tests for SessionActivityTracker class.
Tests reading log files, session management, caching, and integration.
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from daemon.session_activity_tracker import SessionActivityTracker
from shared.data_models import ActivitySessionData, ActivitySessionStatus
from shared.constants import HOOK_LOG_DIR, HOOK_LOG_FILE_PATTERN


class TestSessionActivityTracker(unittest.TestCase):
    """Test cases for SessionActivityTracker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = SessionActivityTracker()
        
        # Create sample activity session data
        self.sample_sessions = [
            ActivitySessionData(
                session_id="session_123",
                start_time=datetime.now(timezone.utc),
                status=ActivitySessionStatus.ACTIVE.value,
                event_type="notification",
                metadata={"message": "Task started"}
            ),
            ActivitySessionData(
                session_id="session_456", 
                start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
                end_time=datetime.now(timezone.utc) - timedelta(minutes=10),
                status=ActivitySessionStatus.STOPPED.value,
                event_type="stop",
                metadata={"reason": "completed"}
            )
        ]
    
    def test_tracker_initialization(self):
        """Test SessionActivityTracker initialization."""
        tracker = SessionActivityTracker()
        
        self.assertIsNotNone(tracker)
        self.assertEqual(len(tracker.get_active_sessions()), 0)
        self.assertIsNotNone(tracker.logger)
    
    def test_get_active_sessions_returns_empty_initially(self):
        """Test get_active_sessions returns empty list initially."""
        sessions = self.tracker.get_active_sessions()
        
        self.assertIsInstance(sessions, list)
        self.assertEqual(len(sessions), 0)
    
    def test_update_from_log_files_processes_log_directory(self):
        """Test update_from_log_files processes hook log files."""
        # Mock the log file discovery and parsing
        sample_log_files = [
            "/fake/logs/claude_activity_2025-07-06.log",
            "/fake/logs/claude_activity_2025-07-05.log"
        ]
        
        with patch.object(self.tracker, '_discover_log_files', return_value=sample_log_files), \
             patch.object(self.tracker, '_process_log_file', side_effect=[
                 [self.sample_sessions[0]], 
                 [self.sample_sessions[1]]
             ]):
            
            result = self.tracker.update_from_log_files()
            
            self.assertTrue(result)
    
    def test_get_sessions_for_period_filters_by_date_range(self):
        """Test get_sessions_for_period filters sessions by date range."""
        # Setup tracker with some sessions
        self.tracker._active_sessions = self.sample_sessions.copy()
        
        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)
        
        filtered_sessions = self.tracker.get_sessions_for_period(start_date, end_date)
        
        self.assertIsInstance(filtered_sessions, list)
        # Should include at least the first session (active within period)
        self.assertGreaterEqual(len(filtered_sessions), 1)
    
    def test_get_session_by_id_returns_correct_session(self):
        """Test get_session_by_id returns the correct session."""
        self.tracker._active_sessions = self.sample_sessions.copy()
        
        session = self.tracker.get_session_by_id("session_123")
        
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, "session_123")
        self.assertEqual(session.status, ActivitySessionStatus.ACTIVE.value)
    
    def test_get_session_by_id_returns_none_if_not_found(self):
        """Test get_session_by_id returns None if session not found."""
        self.tracker._active_sessions = self.sample_sessions.copy()
        
        session = self.tracker.get_session_by_id("nonexistent_session")
        
        self.assertIsNone(session)
    
    def test_discover_log_files_finds_hook_logs(self):
        """Test _discover_log_files finds hook log files in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test log files
            log_files = [
                "claude_activity_2025-07-06.log",
                "claude_activity_2025-07-05.log", 
                "other_file.txt"  # Should be ignored
            ]
            
            for log_file in log_files:
                with open(os.path.join(temp_dir, log_file), 'w') as f:
                    f.write('{"test": "data"}\n')
            
            with patch('daemon.session_activity_tracker.HOOK_LOG_DIR', temp_dir):
                discovered_files = self.tracker._discover_log_files()
            
            # Should find only the claude_activity_*.log files
            self.assertEqual(len(discovered_files), 2)
            self.assertTrue(all('claude_activity_' in f for f in discovered_files))
    
    def test_process_log_file_uses_hook_log_parser(self):
        """Test _process_log_file uses HookLogParser to parse files."""
        mock_parser = Mock()
        mock_parser.parse_log_file.return_value = self.sample_sessions
        
        with patch.object(self.tracker, 'parser', mock_parser):
            sessions = self.tracker._process_log_file("/fake/log/file.log")
        
        self.assertEqual(sessions, self.sample_sessions)
        mock_parser.parse_log_file.assert_called_once_with("/fake/log/file.log")
    
    def test_merge_sessions_consolidates_session_events(self):
        """Test _merge_sessions consolidates multiple events and calculates smart status."""
        # Create multiple events for the same session - recent stop should be WAITING_FOR_USER
        notification_event = ActivitySessionData(
            session_id="session_123",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=2),
            status=ActivitySessionStatus.ACTIVE.value,
            event_type="notification"
        )
        
        stop_event = ActivitySessionData(
            session_id="session_123", 
            start_time=datetime.now(timezone.utc) - timedelta(seconds=30),  # 30 seconds ago = recent
            end_time=datetime.now(timezone.utc),
            status=ActivitySessionStatus.STOPPED.value,
            event_type="stop"
        )
        
        sessions = [notification_event, stop_event]
        
        merged_sessions = self.tracker._merge_sessions(sessions)
        
        # Should consolidate to one session with smart status detection
        self.assertEqual(len(merged_sessions), 1)
        self.assertEqual(merged_sessions[0].session_id, "session_123")
        # Recent stop (30s ago) should be WAITING_FOR_USER according to smart logic
        self.assertEqual(merged_sessions[0].status, ActivitySessionStatus.WAITING_FOR_USER.value)
        
        # Test old stop becomes INACTIVE
        old_stop_event = ActivitySessionData(
            session_id="session_456",
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),  # 1 hour ago = inactive
            status=ActivitySessionStatus.STOPPED.value,
            event_type="stop"
        )
        
        old_merged = self.tracker._merge_sessions([old_stop_event])
        self.assertEqual(old_merged[0].status, ActivitySessionStatus.INACTIVE.value)
    
    def test_is_cache_valid_checks_file_modification_times(self):
        """Test _is_cache_valid checks if cache is still valid based on file modification."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write('{"test": "data"}\n')
            temp_file_path = temp_file.name
        
        try:
            # First call should mark cache as invalid (no cache exists)
            self.assertFalse(self.tracker._is_cache_valid([temp_file_path]))
            
            # After updating cache timestamp and file modification time, should be valid
            self.tracker._last_cache_update = datetime.now()
            # Set the cached modification time to current file time
            self.tracker._file_modification_times[temp_file_path] = os.path.getmtime(temp_file_path)
            self.assertTrue(self.tracker._is_cache_valid([temp_file_path]))
            
        finally:
            os.unlink(temp_file_path)
    
    def test_cleanup_old_sessions_removes_expired_sessions(self):
        """Test cleanup_old_sessions removes sessions older than retention period."""
        old_session = ActivitySessionData(
            session_id="old_session",
            start_time=datetime.now(timezone.utc) - timedelta(days=35),  # Older than 30 days
            status=ActivitySessionStatus.STOPPED.value
        )
        
        recent_session = ActivitySessionData(
            session_id="recent_session", 
            start_time=datetime.now(timezone.utc) - timedelta(days=5),  # Within 30 days
            status=ActivitySessionStatus.ACTIVE.value
        )
        
        self.tracker._active_sessions = [old_session, recent_session]
        
        self.tracker.cleanup_old_sessions()
        
        # Should keep only the recent session
        self.assertEqual(len(self.tracker._active_sessions), 1)
        self.assertEqual(self.tracker._active_sessions[0].session_id, "recent_session")


if __name__ == '__main__':
    unittest.main()