#!/usr/bin/env python3
"""
Tests for DataCollector integration with SessionActivityTracker.
Tests the integration of activity session data with billing session data.
"""

import unittest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from daemon.data_collector import DataCollector
from daemon.session_activity_tracker import SessionActivityTracker
from shared.data_models import ConfigData, MonitoringData, SessionData, ActivitySessionData, ActivitySessionStatus
from shared.constants import DEFAULT_TOTAL_MONTHLY_SESSIONS, DEFAULT_BILLING_START_DAY


class TestDataCollectorIntegration(unittest.TestCase):
    """Test cases for DataCollector integration with SessionActivityTracker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ConfigData(
            total_monthly_sessions=DEFAULT_TOTAL_MONTHLY_SESSIONS,
            refresh_interval_seconds=1,
            billing_start_day=DEFAULT_BILLING_START_DAY
        )
        
        # Mock the ConfigFileManager to avoid file operations
        with patch('shared.file_manager.ConfigFileManager') as mock_config_manager:
            mock_instance = Mock()
            mock_instance.read_data.return_value = {"max_tokens": 35000}
            mock_config_manager.return_value = mock_instance
            
            self.data_collector = DataCollector(self.config)
        
        # Sample activity sessions
        self.sample_activity_sessions = [
            ActivitySessionData(
                session_id="activity_session_1",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=15),
                status=ActivitySessionStatus.ACTIVE.value,
                event_type="notification"
            ),
            ActivitySessionData(
                session_id="activity_session_2",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
                end_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                status=ActivitySessionStatus.STOPPED.value,
                event_type="stop"
            )
        ]
        
        # Sample billing sessions (ccusage data)
        self.sample_billing_sessions = [
            SessionData(
                session_id="billing_session_1",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=20),
                end_time=datetime.now(timezone.utc) - timedelta(minutes=10),
                total_tokens=5000,
                input_tokens=3000,
                output_tokens=2000,
                cost_usd=0.15,
                is_active=False
            )
        ]
    
    def test_data_collector_integrates_activity_tracker(self):
        """Test DataCollector creates and uses SessionActivityTracker."""
        # Test that DataCollector can be enhanced with activity tracker
        self.assertTrue(hasattr(self.data_collector, 'collect_data'))
        
        # After enhancement, should have activity tracker
        activity_tracker = getattr(self.data_collector, '_activity_tracker', None)
        self.assertIsNotNone(activity_tracker)
        self.assertIsInstance(activity_tracker, SessionActivityTracker)
    
    def test_collect_data_includes_activity_sessions(self):
        """Test collect_data method includes activity sessions in MonitoringData."""
        # Mock ccusage data
        mock_ccusage_data = {
            "blocks": [
                {
                    "id": "block_1",
                    "startTime": "2025-07-06T10:00:00Z",
                    "endTime": "2025-07-06T10:10:00Z",
                    "tokenCounts": {"inputTokens": 3000, "outputTokens": 2000},
                    "costUSD": 0.15,
                    "isGap": False
                }
            ]
        }
        
        # Mock the activity tracker
        mock_activity_tracker = Mock(spec=SessionActivityTracker)
        mock_activity_tracker.get_active_sessions.return_value = self.sample_activity_sessions
        mock_activity_tracker.update_from_log_files.return_value = True
        mock_activity_tracker._active_sessions = self.sample_activity_sessions
        
        with patch.object(self.data_collector, 'run_ccusage', return_value=mock_ccusage_data), \
             patch.object(self.data_collector, '_activity_tracker', mock_activity_tracker):
            
            result = self.data_collector.collect_data()
        
        self.assertIsInstance(result, MonitoringData)
        self.assertIsNotNone(result.activity_sessions)
        self.assertEqual(len(result.activity_sessions), 2)
        
        # Verify activity tracker was called
        mock_activity_tracker.update_from_log_files.assert_called_once()
        # Note: We access _active_sessions directly, not get_active_sessions()
    
    def test_collect_data_handles_activity_tracker_failure_gracefully(self):
        """Test collect_data continues working when activity tracker fails."""
        # Mock ccusage data
        mock_ccusage_data = {
            "blocks": [
                {
                    "id": "block_1",
                    "startTime": "2025-07-06T10:00:00Z",
                    "endTime": "2025-07-06T10:10:00Z",
                    "tokenCounts": {"inputTokens": 3000, "outputTokens": 2000},
                    "costUSD": 0.15,
                    "isGap": False
                }
            ]
        }
        
        # Mock activity tracker that fails
        mock_activity_tracker = Mock(spec=SessionActivityTracker)
        mock_activity_tracker.update_from_log_files.side_effect = Exception("Activity tracker failed")
        mock_activity_tracker.get_active_sessions.return_value = []
        
        with patch.object(self.data_collector, 'run_ccusage', return_value=mock_ccusage_data), \
             patch.object(self.data_collector, '_activity_tracker', mock_activity_tracker):
            
            result = self.data_collector.collect_data()
        
        # Should still return valid MonitoringData
        self.assertIsInstance(result, MonitoringData)
        # Activity sessions should be empty due to failure
        self.assertEqual(len(result.activity_sessions or []), 0)
        # But billing sessions should still work
        self.assertGreater(len(result.current_sessions), 0)
    
    def test_collect_data_without_activity_tracker_backwards_compatible(self):
        """Test collect_data works without activity tracker for backwards compatibility."""
        # Mock ccusage data
        mock_ccusage_data = {
            "blocks": [
                {
                    "id": "block_1",
                    "startTime": "2025-07-06T10:00:00Z",
                    "endTime": "2025-07-06T10:10:00Z",
                    "tokenCounts": {"inputTokens": 3000, "outputTokens": 2000},
                    "costUSD": 0.15,
                    "isGap": False
                }
            ]
        }
        
        # Remove activity tracker if it exists
        if hasattr(self.data_collector, '_activity_tracker'):
            delattr(self.data_collector, '_activity_tracker')
        
        with patch.object(self.data_collector, 'run_ccusage', return_value=mock_ccusage_data):
            result = self.data_collector.collect_data()
        
        # Should still return valid MonitoringData
        self.assertIsInstance(result, MonitoringData)
        self.assertGreater(len(result.current_sessions), 0)
        # Activity sessions should be empty list for backwards compatibility
        self.assertEqual(result.activity_sessions, [])
    
    def test_activity_session_cleanup_on_billing_period_change(self):
        """Test activity sessions are cleaned up when billing period changes."""
        # Mock activity tracker with old sessions
        old_sessions = [
            ActivitySessionData(
                session_id="old_session",
                start_time=datetime.now(timezone.utc) - timedelta(days=35),  # Older than billing period
                status=ActivitySessionStatus.STOPPED.value
            )
        ]
        
        mock_activity_tracker = Mock(spec=SessionActivityTracker)
        mock_activity_tracker.get_active_sessions.return_value = []
        mock_activity_tracker.update_from_log_files.return_value = True
        
        with patch.object(self.data_collector, '_activity_tracker', mock_activity_tracker):
            # Simulate billing period change detection
            self.data_collector._handle_activity_session_cleanup()
        
        # Should call cleanup on activity tracker
        mock_activity_tracker.cleanup_old_sessions.assert_called_once()
    
    def test_get_activity_statistics_method(self):
        """Test get_activity_statistics method returns tracker statistics."""
        mock_activity_tracker = Mock(spec=SessionActivityTracker)
        mock_stats = {
            'active_sessions_count': 2,
            'total_sessions_count': 5,
            'cache_hit_ratio': 75.0,
            'background_updates_enabled': True
        }
        mock_activity_tracker.get_statistics.return_value = mock_stats
        
        with patch.object(self.data_collector, '_activity_tracker', mock_activity_tracker):
            stats = self.data_collector.get_activity_statistics()
        
        self.assertEqual(stats, mock_stats)
        mock_activity_tracker.get_statistics.assert_called_once()
    
    def test_get_activity_statistics_without_tracker(self):
        """Test get_activity_statistics returns empty dict without tracker."""
        # Remove activity tracker if it exists
        if hasattr(self.data_collector, '_activity_tracker'):
            delattr(self.data_collector, '_activity_tracker')
        
        stats = self.data_collector.get_activity_statistics()
        
        self.assertEqual(stats, {})


if __name__ == '__main__':
    unittest.main()