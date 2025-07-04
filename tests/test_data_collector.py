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

    @patch('subprocess.run')
    def test_collect_data_success(self, mock_run):
        """Test successful data collection from ccusage."""
        # Mock ccusage output
        mock_ccusage_output = {
            "blocks": [
                {
                    "id": "block-123",
                    "start_time": "2024-07-03T10:00:00Z",
                    "end_time": "2024-07-03T10:30:00Z",
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "cost": 0.05
                }
            ]
        }
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(mock_ccusage_output)
        mock_run.return_value.stderr = ""
        
        result = self.collector.collect_data()
        
        # Verify subprocess call
        mock_run.assert_called_once_with(
            ['ccusage', 'blocks', '-j'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Verify result
        self.assertIsInstance(result, MonitoringData)
        self.assertEqual(len(result.current_sessions), 1)
        self.assertIsInstance(result.current_sessions[0], SessionData)
        self.assertEqual(result.total_sessions_this_month, 1)

    @patch('subprocess.run')
    def test_collect_data_ccusage_failure(self, mock_run):
        """Test handling of ccusage command failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "ccusage: command not found"
        
        # Verify that RuntimeError is raised
        with self.assertRaises(RuntimeError) as context:
            self.collector.collect_data()
        
        self.assertIn("ccusage command failed", str(context.exception))

    @patch('subprocess.run')
    def test_collect_data_json_parse_error(self, mock_run):
        """Test handling of invalid JSON from ccusage."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "invalid json"
        mock_run.return_value.stderr = ""
        
        # Verify that RuntimeError is raised
        with self.assertRaises(RuntimeError) as context:
            self.collector.collect_data()
        
        self.assertIn("Failed to parse JSON", str(context.exception))

    @patch('subprocess.run')
    def test_collect_data_timeout(self, mock_run):
        """Test handling of ccusage command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('ccusage', 30)
        
        # Verify that RuntimeError is raised
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
            "start_time": "2024-07-03T10:00:00Z",
            "end_time": "2024-07-03T10:30:00Z",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost": 0.05
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
            "start_time": "2024-07-03T10:00:00Z"
            # Missing end_time, tokens, cost
        }
        
        with self.assertRaises(KeyError):
            self.collector._parse_ccusage_block(block)

    @patch('time.sleep')
    @patch('subprocess.run')
    def test_collect_data_with_retry(self, mock_run, mock_sleep):
        """Test data collection with retry logic."""
        # First call fails, second succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="temporary error"),
            Mock(returncode=0, stdout='{"blocks": []}', stderr="")
        ]
        
        result = self.collector.collect_data_with_retry(max_retries=2)
        
        # Verify retry happened
        self.assertEqual(mock_run.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # exponential backoff: 2^0 = 1
        self.assertIsInstance(result, MonitoringData)
        self.assertEqual(result.total_sessions_this_month, 0)


if __name__ == '__main__':
    unittest.main()