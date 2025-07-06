#!/usr/bin/env python3

import unittest
import os
import tempfile
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import argparse

from src.client.claude_client import ClaudeClient
from src.shared.data_models import MonitoringData, SessionData


class TestClaudeClient(unittest.TestCase):
    """Test suite for ClaudeClient class following TDD approach."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "monitor_data.json")
        
        # Create sample monitoring data
        self.sample_session = SessionData(
            session_id="test-session-1",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
            end_time=datetime.now(timezone.utc) + timedelta(minutes=30),
            total_tokens=5000,
            input_tokens=2000,
            output_tokens=3000,
            cost_usd=5.25,
            is_active=True
        )
        
        self.sample_monitoring_data = MonitoringData(
            current_sessions=[self.sample_session],
            total_sessions_this_month=15,
            total_cost_this_month=125.75,
            max_tokens_per_session=10000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
        )

    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        os.rmdir(self.temp_dir)

    def test_client_initialization(self):
        """Test client initialization with custom parameters."""
        client = ClaudeClient(
            data_file_path=self.test_file_path,
            total_monthly_sessions=40,
            refresh_interval=2.0
        )
        
        self.assertEqual(client.data_file_path, self.test_file_path)
        self.assertEqual(client.total_monthly_sessions, 40)
        self.assertEqual(client.refresh_interval, 2.0)
        self.assertIsNotNone(client.data_reader)
        self.assertIsNotNone(client.display_manager)

    def test_client_initialization_with_defaults(self):
        """Test client initialization with default parameters."""
        client = ClaudeClient()
        
        # Should use default path
        self.assertIn(".config/claude-monitor/monitor_data.json", client.data_file_path)
        self.assertEqual(client.total_monthly_sessions, 50)
        self.assertEqual(client.refresh_interval, 1.0)

    def test_check_daemon_status_running(self):
        """Test daemon status check when daemon is running."""
        # Write fresh data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        client = ClaudeClient(data_file_path=self.test_file_path)
        is_running = client.check_daemon_status()
        
        self.assertTrue(is_running)

    def test_check_daemon_status_not_running(self):
        """Test daemon status check when daemon is not running."""
        client = ClaudeClient(data_file_path="/nonexistent/path/monitor_data.json")
        is_running = client.check_daemon_status()
        
        self.assertFalse(is_running)

    def test_get_monitoring_data_success(self):
        """Test successful retrieval of monitoring data."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        client = ClaudeClient(data_file_path=self.test_file_path)
        data = client.get_monitoring_data()
        
        self.assertIsInstance(data, MonitoringData)
        self.assertEqual(data.total_sessions_this_month, 15)
        self.assertEqual(data.total_cost_this_month, 125.75)

    def test_get_monitoring_data_no_daemon(self):
        """Test monitoring data retrieval when daemon is not running."""
        client = ClaudeClient(data_file_path="/nonexistent/path/monitor_data.json")
        data = client.get_monitoring_data()
        
        self.assertIsNone(data)

    def test_run_single_iteration(self):
        """Test running a single display iteration."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        client = ClaudeClient(data_file_path=self.test_file_path)
        
        with patch.object(client.display_manager, 'render_full_display') as mock_render:
            result = client.run_single_iteration()
            
            self.assertTrue(result)
            mock_render.assert_called_once()

    def test_run_single_iteration_no_data(self):
        """Test single iteration when no data is available."""
        client = ClaudeClient(data_file_path="/nonexistent/path/monitor_data.json")
        
        with patch.object(client.display_manager, 'render_daemon_offline_display') as mock_offline:
            result = client.run_single_iteration()
            
            self.assertFalse(result)
            mock_offline.assert_called_once()

    def test_show_daemon_not_running_message(self):
        """Test display of daemon not running message."""
        client = ClaudeClient()
        
        with patch.object(client.display_manager, 'show_error_message') as mock_error:
            client.show_daemon_not_running_message()
            mock_error.assert_called_with(
                "Daemon not running. Please start the daemon first or use the original claude_monitor.py"
            )

    @patch('time.sleep')
    def test_run_main_loop_keyboard_interrupt(self, mock_sleep):
        """Test main loop handling of keyboard interrupt."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        client = ClaudeClient(data_file_path=self.test_file_path)
        
        with patch.object(client.display_manager, 'show_exit_message') as mock_exit:
            with patch.object(client.display_manager, 'render_full_display') as mock_render:
                # Mock time.sleep to raise KeyboardInterrupt after first call
                mock_sleep.side_effect = KeyboardInterrupt()
                
                with self.assertRaises(SystemExit):
                    client.run()
                
                mock_exit.assert_called_once()

    def test_parse_arguments_defaults(self):
        """Test argument parsing with default values."""
        client = ClaudeClient()
        args = client.parse_arguments([])
        
        self.assertEqual(args.refresh_interval, 1.0)
        self.assertFalse(args.check_daemon)
        self.assertIsNone(args.data_file)

    def test_parse_arguments_custom(self):
        """Test argument parsing with custom values."""
        client = ClaudeClient()
        args = client.parse_arguments([
            '--refresh-interval', '2.5',
            '--check-daemon',
            '--data-file', '/custom/path/data.json'
        ])
        
        self.assertEqual(args.refresh_interval, 2.5)
        self.assertTrue(args.check_daemon)
        self.assertEqual(args.data_file, '/custom/path/data.json')

    def test_main_function_check_daemon_mode(self):
        """Test main function in check daemon mode."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        args = argparse.Namespace(
            check_daemon=True,
            data_file=self.test_file_path,
            refresh_interval=1.0
        )
        
        client = ClaudeClient()
        with patch('sys.exit') as mock_exit:
            # Make sys.exit actually raise SystemExit to stop execution
            mock_exit.side_effect = SystemExit
            with self.assertRaises(SystemExit):
                client.main(args)
            mock_exit.assert_called_with(0)

    def test_main_function_check_daemon_not_running(self):
        """Test main function when daemon is not running."""
        args = argparse.Namespace(
            check_daemon=True,
            data_file="/nonexistent/path/data.json",
            refresh_interval=1.0
        )
        
        client = ClaudeClient()
        with patch('sys.exit') as mock_exit:
            # Make sys.exit actually raise SystemExit to stop execution
            mock_exit.side_effect = SystemExit
            with self.assertRaises(SystemExit):
                client.main(args)
            mock_exit.assert_called_with(1)

    def test_main_function_normal_mode(self):
        """Test main function in normal display mode."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        args = argparse.Namespace(
            check_daemon=False,
            data_file=self.test_file_path,
            refresh_interval=1.0
        )
        
        client = ClaudeClient(
            data_file_path=self.test_file_path,
            refresh_interval=1.0
        )
        
        # Patch the run method to avoid infinite loop
        with patch.object(client, 'run', return_value=None) as mock_run:
            client.main(args)
            mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()