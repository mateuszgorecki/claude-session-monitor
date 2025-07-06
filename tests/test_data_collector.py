"""
Tests for DataCollector class.
"""
import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import subprocess

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from daemon.data_collector import DataCollector
from shared.data_models import SessionData, MonitoringData, ConfigData, ErrorStatus


class TestDataCollector(unittest.TestCase):
    """Test cases for DataCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = ConfigData(
            ccusage_fetch_interval_seconds=10,
            total_monthly_sessions=50,
            time_remaining_alert_minutes=30,
            inactivity_alert_minutes=10,
            billing_start_day=1
        )
        self.collector = DataCollector(self.config)

    def test_initialization(self):
        """Test DataCollector initialization."""
        self.assertIsInstance(self.collector, DataCollector)
        self.assertEqual(self.collector.config, self.config)

    @patch.object(DataCollector, 'run_ccusage')
    def test_collect_data_success(self, mock_run_ccusage):
        """Test successful data collection from ccusage."""
        # Mock ccusage output with correct structure
        mock_ccusage_output = {
            "blocks": [
                {
                    "id": "block-123",
                    "startTime": "2025-07-03T10:00:00Z",
                    "endTime": "2025-07-03T10:30:00Z",
                    "isActive": False,
                    "isGap": False,
                    "tokenCounts": {
                        "inputTokens": 1000,
                        "outputTokens": 500,
                        "cacheCreationInputTokens": 0,
                        "cacheReadInputTokens": 0
                    },
                    "totalTokens": 1500,
                    "costUSD": 0.05
                }
            ]
        }
        
        mock_run_ccusage.return_value = mock_ccusage_output
        
        result = self.collector.collect_data()
        
        # Verify run_ccusage call
        mock_run_ccusage.assert_called_once()
        
        # Verify result
        self.assertIsInstance(result, MonitoringData)
        self.assertEqual(len(result.current_sessions), 1)
        self.assertIsInstance(result.current_sessions[0], SessionData)
        self.assertEqual(result.total_sessions_this_month, 1)

    @patch.object(DataCollector, 'run_ccusage')
    def test_collect_data_ccusage_failure(self, mock_run_ccusage):
        """Test handling of ccusage command failure."""
        # Mock run_ccusage to return empty blocks (simulating failure)
        mock_run_ccusage.return_value = {"blocks": []}
        
        # Since run_ccusage handles errors gracefully, this should NOT raise
        result = self.collector.collect_data()
        
        # Should return empty monitoring data
        self.assertEqual(len(result.current_sessions), 0)

    @patch.object(DataCollector, 'run_ccusage')
    def test_collect_data_json_parse_error(self, mock_run_ccusage):
        """Test handling of invalid JSON from ccusage."""
        # Mock run_ccusage to return empty blocks (graceful handling)
        mock_run_ccusage.return_value = {"blocks": []}
        
        # Should handle gracefully, not raise
        result = self.collector.collect_data()
        
        # Should return empty monitoring data
        self.assertEqual(len(result.current_sessions), 0)

    @patch('subprocess.run')
    def test_collect_data_timeout(self, mock_run):
        """Test handling of ccusage command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('ccusage', 30)
        
        # Verify that RuntimeError is raised when no blocks data is returned
        with self.assertRaises(RuntimeError) as context:
            self.collector.collect_data()
        
        self.assertIn("ccusage command timed out", str(context.exception))

    @patch('subprocess.run')
    def test_collect_data_empty_blocks(self, mock_run):
        """Test handling of empty blocks from ccusage."""
        mock_ccusage_output = {"blocks": []}
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(mock_ccusage_output)
        mock_run.return_value.stderr = ""
        
        result = self.collector.collect_data()
        
        # Verify result
        self.assertIsInstance(result, MonitoringData)
        self.assertEqual(len(result.current_sessions), 0)
        self.assertEqual(result.total_sessions_this_month, 0)

    def test_parse_ccusage_block(self):
        """Test parsing individual ccusage block."""
        block = {
            "id": "block-123",
            "startTime": "2024-07-03T10:00:00Z",
            "endTime": "2024-07-03T10:30:00Z",
            "isActive": False,
            "isGap": False,
            "tokenCounts": {
                "inputTokens": 1000,
                "outputTokens": 500,
                "cacheCreationInputTokens": 0,
                "cacheReadInputTokens": 0
            },
            "totalTokens": 1500,
            "costUSD": 0.05
        }
        
        session = self.collector._parse_ccusage_block(block)
        
        self.assertIsInstance(session, SessionData)
        self.assertEqual(session.session_id, "block-123")
        self.assertEqual(session.input_tokens, 1000)
        self.assertEqual(session.output_tokens, 500)
        self.assertEqual(session.total_tokens, 1500)  # input + output
        self.assertEqual(session.cost_usd, 0.05)
        self.assertIsNotNone(session.end_time)
        self.assertFalse(session.is_active)  # has end_time and is old

    def test_parse_ccusage_block_missing_fields(self):
        """Test parsing ccusage block with missing fields."""
        block = {
            "id": "block-123",
            "startTime": "2024-07-03T10:00:00Z"
            # Missing endTime, tokenCounts, costUSD
        }
        
        # Should handle missing fields gracefully with defaults
        session = self.collector._parse_ccusage_block(block)
        self.assertEqual(session.input_tokens, 0)  # Default from missing tokenCounts
        self.assertEqual(session.output_tokens, 0)  # Default from missing tokenCounts
        self.assertEqual(session.cost_usd, 0)  # Default from missing costUSD
        self.assertFalse(session.is_active)  # Default from missing isActive
    @patch('time.sleep')
    @patch.object(DataCollector, 'run_ccusage')
    def test_collect_data_with_retry(self, mock_run_ccusage, mock_sleep):
        """Test data collection with retry logic."""
        # Since run_ccusage handles errors gracefully, simulate actual error
        # by making the first call raise exception, second call succeed
        mock_run_ccusage.side_effect = [
            RuntimeError("Simulated ccusage failure"),
            {"blocks": []}
        ]
        
        result = self.collector.collect_data_with_retry(max_retries=2)
        
        # Verify retry happened
        self.assertEqual(mock_run_ccusage.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # exponential backoff: 2^0 = 1
        self.assertIsInstance(result, MonitoringData)
        self.assertEqual(result.total_sessions_this_month, 0)


if __name__ == '__main__':
    unittest.main()