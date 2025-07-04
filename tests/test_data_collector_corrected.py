"""
Tests for corrected DataCollector implementation matching claude_monitor.py logic.
This file contains TDD tests for the 8 critical issues identified in the current implementation.
"""
import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, date, timedelta
import subprocess

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from daemon.data_collector import DataCollector
from shared.data_models import SessionData, MonitoringData, ConfigData, ErrorStatus


class TestDataCollectorCorrected(unittest.TestCase):
    """Test cases for corrected DataCollector implementation."""

    def setUp(self):
        """Set up test fixtures with correct ccusage structure."""
        self.config = ConfigData(
            ccusage_fetch_interval_seconds=10,
            total_monthly_sessions=50,
            time_remaining_alert_minutes=30,
            inactivity_alert_minutes=10,
            billing_start_day=15  # Non-default billing start day
        )
        self.collector = DataCollector(self.config)

        # Real ccusage structure based on actual output
        self.sample_ccusage_output = {
            "blocks": [
                {
                    "id": "2025-06-18T08:00:00.000Z",
                    "startTime": "2025-06-18T08:00:00.000Z",
                    "endTime": "2025-06-18T13:00:00.000Z",
                    "actualEndTime": "2025-06-18T12:57:59.777Z",
                    "isActive": False,
                    "isGap": False,
                    "entries": 527,
                    "tokenCounts": {
                        "inputTokens": 5941,
                        "outputTokens": 23196,
                        "cacheCreationInputTokens": 1094754,
                        "cacheReadInputTokens": 19736284
                    },
                    "totalTokens": 29137,
                    "costUSD": 16.636553099999986,
                    "models": ["claude-sonnet-4", "claude-opus-4"],
                    "burnRate": None,
                    "projection": None
                },
                {
                    "id": "2025-06-18T13:00:00.000Z",
                    "startTime": "2025-06-18T13:00:00.000Z",
                    "endTime": "2025-06-18T18:00:00.000Z",
                    "actualEndTime": None,  # Active session
                    "isActive": True,
                    "isGap": False,
                    "entries": 150,
                    "tokenCounts": {
                        "inputTokens": 2500,
                        "outputTokens": 8000,
                        "cacheCreationInputTokens": 0,
                        "cacheReadInputTokens": 500000
                    },
                    "totalTokens": 10500,
                    "costUSD": 5.25,
                    "models": ["claude-sonnet-4"],
                    "burnRate": None,
                    "projection": None
                }
            ]
        }

    @patch('subprocess.run')
    def test_run_ccusage_with_since_parameter(self, mock_run):
        """Test that ccusage is called with -s parameter for optimization."""
        # Setup mock
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(self.sample_ccusage_output)
        mock_run.return_value.stderr = ""
        
        # Test call with since parameter
        result = self.collector.run_ccusage(since_date="20250615")
        
        # Verify the command was called with -s parameter
        expected_command = ['ccusage', 'blocks', '-j', '-s', '20250615']
        mock_run.assert_called_once_with(
            expected_command,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Verify result
        self.assertEqual(result, self.sample_ccusage_output)

    @patch('subprocess.run')
    def test_run_ccusage_without_since_parameter(self, mock_run):
        """Test that ccusage is called without -s when since_date is None."""
        # Setup mock
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(self.sample_ccusage_output)
        mock_run.return_value.stderr = ""
        
        # Test call without since parameter
        result = self.collector.run_ccusage(since_date=None)
        
        # Verify the command was called without -s parameter
        expected_command = ['ccusage', 'blocks', '-j']
        mock_run.assert_called_once_with(
            expected_command,
            capture_output=True,
            text=True,
            check=True
        )

    def test_parse_ccusage_block_with_nested_tokens(self):
        """Test parsing ccusage block with correct nested tokenCounts structure."""
        block = self.sample_ccusage_output["blocks"][0]
        
        session = self.collector._parse_ccusage_block(block)
        
        # Verify correct field names and structure
        self.assertEqual(session.session_id, "2025-06-18T08:00:00.000Z")
        self.assertEqual(session.input_tokens, 5941)  # From tokenCounts.inputTokens
        self.assertEqual(session.output_tokens, 23196)  # From tokenCounts.outputTokens
        self.assertEqual(session.total_tokens, 29137)  # From totalTokens (not sum)
        self.assertEqual(session.cost_usd, 16.636553099999986)  # From costUSD
        self.assertFalse(session.is_active)  # From isActive field
        
        # Verify correct timestamp parsing
        expected_start = datetime.fromisoformat('2025-06-18T08:00:00.000Z'.replace('Z', '+00:00'))
        expected_end = datetime.fromisoformat('2025-06-18T13:00:00.000Z'.replace('Z', '+00:00'))
        self.assertEqual(session.start_time, expected_start)
        self.assertEqual(session.end_time, expected_end)

    def test_parse_ccusage_block_active_session(self):
        """Test parsing active session with isActive=True."""
        block = self.sample_ccusage_output["blocks"][1]  # Active session
        
        session = self.collector._parse_ccusage_block(block)
        
        # Verify active session is correctly identified
        self.assertTrue(session.is_active)  # Should use isActive flag, not time calculation
        self.assertEqual(session.input_tokens, 2500)
        self.assertEqual(session.output_tokens, 8000)
        self.assertEqual(session.total_tokens, 10500)

    def test_subscription_period_calculation(self):
        """Test billing period start calculation matches original logic."""
        # Test current month scenario (today >= billing_start_day)
        with patch('daemon.data_collector.date') as mock_date:
            mock_date.today.return_value = date(2025, 6, 20)  # After 15th
            
            result = self.collector.get_subscription_period_start(15)
            expected = date(2025, 6, 15)
            self.assertEqual(result, expected)
        
        # Test previous month scenario (today < billing_start_day)
        with patch('daemon.data_collector.date') as mock_date:
            mock_date.today.return_value = date(2025, 6, 10)  # Before 15th
            
            result = self.collector.get_subscription_period_start(15)
            expected = date(2025, 5, 15)
            self.assertEqual(result, expected)

    def test_incremental_fetch_strategy(self):
        """Test intelligent fetch strategy with different scenarios."""
        # Mock config data
        mock_config = {
            "force_recalculate": False,
            "max_tokens": 50000,
            "monthly_meta": {"period_start": "2025-06-15"},
            "last_incremental_update": "2025-06-18"
        }
        
        # Test incremental update scenario
        with patch('daemon.data_collector.date') as mock_date:
            mock_date.today.return_value = date(2025, 6, 20)
            
            strategy = self.collector.determine_fetch_strategy(mock_config, 15)
            
            # Should return date 2 days before last update for safety
            expected_date = datetime.strptime("2025-06-18", '%Y-%m-%d') - timedelta(days=2)
            expected = expected_date.strftime('%Y%m%d')
            self.assertEqual(strategy, expected)

    @patch('subprocess.run')
    def test_active_session_detection_by_time_range(self, mock_run):
        """Test active session detection using time range, not arbitrary 5-minute window."""
        # Setup mock with current time inside an active session
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(self.sample_ccusage_output)
        
        # Mock current time to be within the active session range
        test_time = datetime.fromisoformat('2025-06-18T15:30:00.000Z'.replace('Z', '+00:00'))
        
        with patch('daemon.data_collector.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            active_session = self.collector.find_active_session(
                self.sample_ccusage_output["blocks"], 
                test_time
            )
            
            # Should find the second block (active session) based on time range
            self.assertIsNotNone(active_session)
            self.assertEqual(active_session["id"], "2025-06-18T13:00:00.000Z")

    def test_processed_sessions_tracking(self):
        """Test tracking of processed sessions to prevent duplicate counting."""
        # Setup processed sessions list
        processed_sessions = ["2025-06-18T08:00:00.000Z"]  # First session already processed
        
        # Test filtering
        new_sessions = self.collector.filter_unprocessed_sessions(
            self.sample_ccusage_output["blocks"],
            processed_sessions
        )
        
        # Should only return the second session (not processed yet)
        self.assertEqual(len(new_sessions), 1)
        self.assertEqual(new_sessions[0]["id"], "2025-06-18T13:00:00.000Z")

    def test_max_tokens_persistence(self):
        """Test persistence and updating of maximum tokens value."""
        # Setup current max
        current_max = 25000
        
        # Test with blocks containing higher token count
        blocks = self.sample_ccusage_output["blocks"]
        
        new_max = self.collector.calculate_new_max_tokens(blocks, current_max)
        
        # Should find the higher value (29137 from first block)
        self.assertEqual(new_max, 29137)
        
        # Test with no higher values
        lower_max = 50000
        new_max = self.collector.calculate_new_max_tokens(blocks, lower_max)
        
        # Should keep existing max
        self.assertEqual(new_max, lower_max)

    def test_cache_expiration_logic(self):
        """Test 10-second cache mechanism for ccusage data."""
        # Test cache miss (first call)
        with patch('time.time', return_value=1000):
            self.collector._last_fetch_time = 0
            should_fetch = self.collector.should_fetch_new_data()
            self.assertTrue(should_fetch)
        
        # Test cache hit (recent call)
        with patch('time.time', return_value=1005):  # 5 seconds later
            self.collector._last_fetch_time = 1000
            should_fetch = self.collector.should_fetch_new_data()
            self.assertFalse(should_fetch)
        
        # Test cache expiration (>10 seconds)
        with patch('time.time', return_value=1015):  # 15 seconds later
            self.collector._last_fetch_time = 1000
            should_fetch = self.collector.should_fetch_new_data()
            self.assertTrue(should_fetch)


if __name__ == '__main__':
    unittest.main()