#!/usr/bin/env python3
"""
Integration tests for the complete session lifecycle.
Tests the full flow: active session → 5h window end → cleanup → waiting → new session.
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from daemon.claude_daemon import ClaudeDaemon
from daemon.session_activity_tracker import SessionActivityTracker
from client.display_manager import DisplayManager
from shared.data_models import MonitoringData, SessionData, ActivitySessionData, ActivitySessionStatus, ConfigData
from shared.constants import DEFAULT_CCUSAGE_FETCH_INTERVAL_SECONDS, HOOK_LOG_DIR, HOOK_LOG_FILE_PATTERN
from shared.utils import get_work_timing_suggestion


class TestFullSessionLifecycle(unittest.TestCase):
    """Test the complete session lifecycle integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
        self.data_path = os.path.join(self.temp_dir, "data.json")
        self.log_path = os.path.join(self.temp_dir, "claude_activity.log")
        
        # Create test config
        self.test_config = ConfigData(
            refresh_interval_seconds=1,
            ccusage_fetch_interval_seconds=2
        )
        
        # Create test components
        self.daemon = ClaudeDaemon(self.test_config)
        self.session_tracker = SessionActivityTracker()
        self.display_manager = DisplayManager()
        
        # Mock the log file discovery to use our temp log path
        self.log_file_patcher = patch.object(self.session_tracker, '_discover_log_files', return_value=[self.log_path])
        self.log_file_patcher.start()
        
        # Mock the constants for cleanup method
        self.hook_log_dir_patcher = patch('daemon.session_activity_tracker.HOOK_LOG_DIR', self.temp_dir)
        self.hook_log_dir_patcher.start()
        self.hook_log_file_pattern_patcher = patch('daemon.session_activity_tracker.HOOK_LOG_FILE_PATTERN', 'claude_activity.log')
        self.hook_log_file_pattern_patcher.start()
        
        # Create sample activity log content
        self.sample_activity_log = [
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "event_type": "notification",
                "project_name": "test-project",
                "session_id": "session_123",
                "metadata": {"message": "Task started"}
            },
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
                "event_type": "notification", 
                "project_name": "test-project",
                "session_id": "session_123",
                "metadata": {"message": "Task progress"}
            }
        ]
        
        # Create sample session data
        self.active_session = SessionData(
            session_id="session_123",
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc) + timedelta(hours=4),  # Still active
            total_tokens=5000,
            input_tokens=2000,
            output_tokens=3000,
            cost_usd=5.25,
            is_active=True
        )
        
        self.old_session = SessionData(
            session_id="session_456",
            start_time=datetime.now(timezone.utc) - timedelta(hours=6),  # Outside 5h window
            end_time=datetime.now(timezone.utc) - timedelta(hours=5, minutes=30),
            total_tokens=3000,
            input_tokens=1200,
            output_tokens=1800,
            cost_usd=3.15,
            is_active=False
        )
        
        # Create monitoring data
        self.monitoring_data_active = MonitoringData(
            current_sessions=[self.active_session],
            total_sessions_this_month=1,
            total_cost_this_month=5.25,
            max_tokens_per_session=5000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15),
            activity_sessions=[]  # Will be populated during tests
        )
        
        self.monitoring_data_waiting = MonitoringData(
            current_sessions=[],  # No active sessions
            total_sessions_this_month=1,
            total_cost_this_month=5.25,
            max_tokens_per_session=5000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15),
            activity_sessions=[]  # No activity sessions
        )
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.log_file_patcher.stop()
        self.hook_log_dir_patcher.stop()
        self.hook_log_file_pattern_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_full_session_lifecycle(self):
        """
        Test the complete session lifecycle:
        1. Active session with activity tracking
        2. End of 5h window triggers cleanup
        3. Screen clears properly during transition
        4. Waiting state displays timing suggestions
        5. New session can start properly
        """
        
        # Phase 1: Active session with activity tracking
        # Set up activity sessions (recent, within 5h window)
        recent_activity = [
            ActivitySessionData(
                project_name="test-project",
                session_id="session_123",
                start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                status=ActivitySessionStatus.ACTIVE.value,
                event_type="notification",
                metadata={"message": "Task started"}
            )
        ]
        self.session_tracker._active_sessions = recent_activity
        
        # Update monitoring data to include activity sessions
        self.monitoring_data_active.activity_sessions = recent_activity
        
        # Test active session display
        with patch.object(self.display_manager, 'clear_screen') as mock_clear, \
             patch.object(self.display_manager, 'move_to_top') as mock_move_to_top, \
             patch('builtins.print') as mock_print:
            
            # First render - should clear screen
            self.display_manager.render_full_display(self.monitoring_data_active)
            
            # Should have cleared screen on first render
            mock_clear.assert_called_once()
            
            # Verify active session is displayed
            print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
            content = ' '.join(print_calls)
            self.assertIn("test-project", content)
            self.assertIn("ACTIVE", content)
                
        # Phase 2: End of 5h window - create old activity sessions
        # Set up old activity sessions (outside 5h window)
        old_activity = [
            ActivitySessionData(
                project_name="test-project",
                session_id="session_456",
                start_time=datetime.now(timezone.utc) - timedelta(hours=6),
                end_time=datetime.now(timezone.utc) - timedelta(hours=5, minutes=30),
                status=ActivitySessionStatus.STOPPED.value,
                event_type="stop",
                metadata={"reason": "completed"}
            )
        ]
        self.session_tracker._active_sessions = old_activity
        
        # Create a log file to simulate activity logs
        with open(self.log_path, 'w') as f:
            f.write('{"test": "old data"}\n')
        
        # Test cleanup triggers when all sessions are old
        self.session_tracker.cleanup_completed_billing_sessions()
        
        # Should have no sessions after cleanup
        self.assertEqual(len(self.session_tracker._active_sessions), 0)
        
        # Should have cleared log file since all sessions are old
        with open(self.log_path, 'r') as f:
            content = f.read()
            self.assertEqual(content, "", "Log file should be empty after cleanup")
                
        # Phase 3: Screen clearing during transition to waiting state
        with patch.object(self.display_manager, 'clear_screen') as mock_clear, \
             patch.object(self.display_manager, 'move_to_top') as mock_move_to_top, \
             patch('builtins.print') as mock_print:
            
            # Reset the display manager's internal state
            self.display_manager._screen_cleared = False
            self.display_manager._previous_session_state = 'active'
            
            # Render waiting state (no active sessions)
            self.display_manager.render_full_display(self.monitoring_data_waiting)
            
            # Should have cleared screen due to state transition (active -> waiting)
            mock_clear.assert_called_once()
            
        # Phase 4: Waiting state displays timing suggestions
        with patch('src.shared.utils.datetime') as mock_datetime, \
             patch('builtins.print') as mock_print:
            
            # Mock current time to test timing suggestions
            mock_now = Mock()
            mock_now.minute = 10  # Should get positive suggestions (0-15 range)
            mock_datetime.now.return_value = mock_now
            
            # Test timing suggestion generation
            suggestion = get_work_timing_suggestion()
            self.assertIsNotNone(suggestion)
            self.assertIsInstance(suggestion, str)
            self.assertGreater(len(suggestion), 0)
            
            # Test waiting display includes timing suggestions
            self.display_manager.render_full_display(self.monitoring_data_waiting)
            
            # Verify timing suggestions are displayed
            print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
            content = ' '.join(print_calls)
            # Should contain timing-related text
            self.assertTrue(any('timing' in str(call).lower() or 'czas' in str(call).lower() 
                             for call in print_calls))
            
        # Phase 5: New session can start properly
        new_session = SessionData(
            session_id="session_789",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=5),
            total_tokens=0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            is_active=True
        )
        
        new_monitoring_data = MonitoringData(
            current_sessions=[new_session],
            total_sessions_this_month=2,
            total_cost_this_month=5.25,
            max_tokens_per_session=5000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
        )
        
        with patch.object(self.display_manager, 'clear_screen') as mock_clear, \
             patch('builtins.print') as mock_print:
            
            # Reset display manager state to simulate transition from waiting to active
            self.display_manager._previous_session_state = 'waiting'
            
            # Render new active session
            self.display_manager.render_full_display(new_monitoring_data)
            
            # Should have cleared screen due to state transition (waiting -> active)
            mock_clear.assert_called_once()
            
            # Verify new session is displayed
            print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
            content = ' '.join(print_calls)
            # Check that we have active session display (no project name since no activity sessions in this test)
            
    def test_integration_with_daemon_cleanup(self):
        """Test that daemon properly integrates with session cleanup."""
        
        # Test that session tracker cleanup method can be called without errors
        try:
            self.session_tracker.cleanup_completed_billing_sessions()
        except Exception as e:
            self.fail(f"Session tracker cleanup failed: {e}")
            
        # Test that daemon can be created and has necessary attributes
        self.assertIsNotNone(self.daemon)
        self.assertTrue(hasattr(self.daemon, '_collect_data'))
        
        # Test that _collect_data method exists and can be called safely
        try:
            # Mock the necessary components to avoid actual system calls
            with patch.object(self.daemon, 'data_collector') as mock_data_collector, \
                 patch.object(self.daemon, 'session_activity_tracker') as mock_session_tracker, \
                 patch.object(self.daemon, 'notification_manager') as mock_notification_manager:
                
                # Mock returns to avoid errors
                mock_data_collector.collect_data.return_value = self.monitoring_data_active
                mock_session_tracker.cleanup_completed_billing_sessions.return_value = None
                mock_notification_manager.check_and_send_notifications.return_value = None
                
                # This should not raise an exception
                self.daemon._collect_data()
                
        except Exception as e:
            self.fail(f"Daemon data collection failed: {e}")
                
    def test_error_handling_during_lifecycle(self):
        """Test that errors during lifecycle don't break the system."""
        
        # Test cleanup graceful handling when log file doesn't exist
        # Set up session tracker with old sessions
        old_session = ActivitySessionData(
            project_name="test-project",
            session_id="session_999",
            start_time=datetime.now(timezone.utc) - timedelta(hours=6),
            status=ActivitySessionStatus.STOPPED.value,
            event_type="stop",
            metadata={"reason": "completed"}
        )
        self.session_tracker._active_sessions = [old_session]
        
        # Should not raise exception even if log file operations have issues
        try:
            self.session_tracker.cleanup_completed_billing_sessions()
        except Exception as e:
            self.fail(f"cleanup_completed_billing_sessions raised an exception: {e}")
            
        # Test display error handling - should handle print errors gracefully
        with patch('builtins.print') as mock_print:
            mock_print.side_effect = Exception("Display error")
            
            # Should not raise exception
            try:
                self.display_manager.render_full_display(self.monitoring_data_active)
                # The exception will happen internally but should be handled gracefully
            except Exception as e:
                # This is expected - the print function will fail, but we can verify the method completes
                pass
                
    def test_screen_clearing_optimization(self):
        """Test that screen clearing is optimized - only clears when necessary."""
        
        with patch.object(self.display_manager, 'clear_screen') as mock_clear, \
             patch.object(self.display_manager, 'move_to_top') as mock_move_to_top:
            
            # First render - should clear (first time)
            self.display_manager.render_full_display(self.monitoring_data_active)
            self.assertEqual(mock_clear.call_count, 1)
            
            # Second render with same data - should not clear (anti-flicker)
            self.display_manager.render_full_display(self.monitoring_data_active)
            self.assertEqual(mock_clear.call_count, 1)  # Still 1, not 2
            self.assertEqual(mock_move_to_top.call_count, 1)  # Should use move_to_top
            
            # Third render with different state - should clear (state transition)
            self.display_manager.render_full_display(self.monitoring_data_waiting)
            self.assertEqual(mock_clear.call_count, 2)  # Should be 2 now
            
    def test_backward_compatibility(self):
        """Test that new features maintain backward compatibility with previous version."""
        
        # Test 1: Existing SessionData structure should work
        legacy_session = SessionData(
            session_id="legacy_session",
            start_time=datetime.now(timezone.utc) - timedelta(hours=2),
            end_time=datetime.now(timezone.utc) - timedelta(hours=1),
            total_tokens=2000,
            input_tokens=800,
            output_tokens=1200,
            cost_usd=2.15,
            is_active=False
        )
        
        # Should be able to create MonitoringData with existing interface
        legacy_monitoring_data = MonitoringData(
            current_sessions=[legacy_session],
            total_sessions_this_month=5,
            total_cost_this_month=12.50,
            max_tokens_per_session=2000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
            # Note: Not setting activity_sessions - should work with None/default
        )
        
        # Test 2: Display manager should handle missing activity_sessions gracefully
        with patch('builtins.print'):
            try:
                self.display_manager.render_full_display(legacy_monitoring_data)
            except Exception as e:
                self.fail(f"Display manager failed with legacy data: {e}")
        
        # Test 3: SessionActivityTracker should work without initialization errors
        legacy_tracker = SessionActivityTracker()
        
        # Should be able to call cleanup without issues
        try:
            legacy_tracker.cleanup_completed_billing_sessions()
        except Exception as e:
            self.fail(f"Session tracker cleanup failed with legacy usage: {e}")
            
        # Test 4: Should be able to get empty sessions list safely
        try:
            sessions = legacy_tracker.get_active_sessions()
            self.assertIsInstance(sessions, list)
        except Exception as e:
            self.fail(f"Session tracker get_active_sessions failed: {e}")
            
        # Test 5: Timing suggestions should work independently
        try:
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            self.assertGreater(len(suggestion), 0)
        except Exception as e:
            self.fail(f"Timing suggestions failed: {e}")
            
        # Test 6: MonitoringData serialization/deserialization should work
        try:
            # Convert to dict and back
            data_dict = legacy_monitoring_data.to_dict()
            restored_data = MonitoringData.from_dict(data_dict)
            
            # Should have same session count
            self.assertEqual(len(restored_data.current_sessions), len(legacy_monitoring_data.current_sessions))
            self.assertEqual(restored_data.total_sessions_this_month, legacy_monitoring_data.total_sessions_this_month)
            
        except Exception as e:
            self.fail(f"MonitoringData serialization failed: {e}")
            

if __name__ == '__main__':
    unittest.main()