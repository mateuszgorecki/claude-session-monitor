#!/usr/bin/env python3

import unittest
import os
import tempfile
import json
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Add the project root to path to import the smart wrapper
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from claude_monitor_smart import SmartClaudeMonitor
from src.shared.data_models import MonitoringData, SessionData


class TestSmartWrapper(unittest.TestCase):
    """Test suite for SmartClaudeMonitor wrapper."""

    def setUp(self):
        """Set up test fixtures."""
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
        """Clean up after tests."""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test smart wrapper initialization."""
        wrapper = SmartClaudeMonitor()
        
        # Should have default data file path
        self.assertIn(".config/claude-monitor/monitor_data.json", wrapper.data_file_path)

    def test_is_daemon_running_true(self):
        """Test daemon detection when daemon is running."""
        # Create fresh data file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = self.test_file_path
        
        self.assertTrue(wrapper.is_daemon_running())

    def test_is_daemon_running_false(self):
        """Test daemon detection when daemon is not running."""
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = "/nonexistent/path/monitor_data.json"
        
        self.assertFalse(wrapper.is_daemon_running())

    @patch('builtins.print')
    def test_show_daemon_info_running(self, mock_print):
        """Test daemon info display when daemon is running."""
        # Create fresh data file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = self.test_file_path
        
        wrapper.show_daemon_info()
        
        # Check that appropriate messages were printed
        printed_text = ' '.join([call.args[0] for call in mock_print.call_args_list])
        self.assertIn("Daemon is running", printed_text)
        self.assertIn("using new client", printed_text)

    @patch('builtins.print')
    def test_show_daemon_info_not_running(self, mock_print):
        """Test daemon info display when daemon is not running."""
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = "/nonexistent/path/monitor_data.json"
        
        wrapper.show_daemon_info()
        
        # Check that appropriate messages were printed
        printed_text = ' '.join([call.args[0] for call in mock_print.call_args_list])
        self.assertIn("Daemon not running", printed_text)
        self.assertIn("using original monitor", printed_text)

    def test_parse_arguments_daemon_info(self):
        """Test parsing --daemon-info argument."""
        wrapper = SmartClaudeMonitor()
        
        with patch('sys.argv', ['script', '--daemon-info']):
            args, remaining = wrapper.parse_arguments()
            
            self.assertTrue(args.daemon_info)
            self.assertEqual(remaining, [])

    def test_parse_arguments_force_direct(self):
        """Test parsing --force-direct argument."""
        wrapper = SmartClaudeMonitor()
        
        with patch('sys.argv', ['script', '--force-direct', '--start-day', '15']):
            args, remaining = wrapper.parse_arguments()
            
            self.assertTrue(args.force_direct)
            self.assertEqual(remaining, ['--start-day', '15'])

    def test_parse_arguments_force_daemon(self):
        """Test parsing --force-daemon argument."""
        wrapper = SmartClaudeMonitor()
        
        with patch('sys.argv', ['script', '--force-daemon', '--timezone', 'UTC']):
            args, remaining = wrapper.parse_arguments()
            
            self.assertTrue(args.force_daemon)
            self.assertEqual(remaining, ['--timezone', 'UTC'])

    @patch('builtins.print')
    @patch('claude_monitor_smart.SmartClaudeMonitor.run_new_client')
    def test_main_daemon_mode_auto_detect(self, mock_run_new, mock_print):
        """Test main function auto-detecting daemon mode."""
        # Create fresh data file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = self.test_file_path
        
        with patch('sys.argv', ['script']):
            wrapper.main()
            
            mock_run_new.assert_called_once()

    @patch('builtins.print')
    @patch('claude_monitor_smart.SmartClaudeMonitor.run_original_monitor')
    def test_main_direct_mode_auto_detect(self, mock_run_original, mock_print):
        """Test main function auto-detecting direct mode."""
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = "/nonexistent/path/monitor_data.json"
        
        with patch('sys.argv', ['script']):
            wrapper.main()
            
            mock_run_original.assert_called_once_with([])

    @patch('builtins.print')
    @patch('claude_monitor_smart.SmartClaudeMonitor.run_original_monitor')
    def test_main_force_direct_mode(self, mock_run_original, mock_print):
        """Test main function with forced direct mode."""
        # Even with daemon running, should use direct mode
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = self.test_file_path
        
        with patch('sys.argv', ['script', '--force-direct', '--start-day', '15']):
            wrapper.main()
            
            mock_run_original.assert_called_once_with(['--start-day', '15'])

    @patch('builtins.print')
    @patch('claude_monitor_smart.SmartClaudeMonitor.run_new_client')
    def test_main_force_daemon_mode(self, mock_run_new, mock_print):
        """Test main function with forced daemon mode."""
        # Even without daemon running, should use daemon mode
        wrapper = SmartClaudeMonitor()
        wrapper.data_file_path = "/nonexistent/path/monitor_data.json"
        
        with patch('sys.argv', ['script', '--force-daemon']):
            wrapper.main()
            
            mock_run_new.assert_called_once()

    @patch('builtins.print')
    @patch('claude_monitor_smart.SmartClaudeMonitor.show_daemon_info')
    def test_main_daemon_info_mode(self, mock_show_info, mock_print):
        """Test main function with daemon info request."""
        wrapper = SmartClaudeMonitor()
        
        with patch('sys.argv', ['script', '--daemon-info']):
            wrapper.main()
            
            mock_show_info.assert_called_once()

    @patch('claude_monitor_smart.SmartClaudeMonitor.run_original_monitor')
    def test_main_help_mode(self, mock_run_original):
        """Test main function with help request."""
        wrapper = SmartClaudeMonitor()
        
        with patch('sys.argv', ['script', '--help']):
            with patch('builtins.print'):
                wrapper.main()
                
                # Should call original monitor with --help
                mock_run_original.assert_called_once_with(['--help'])

    @patch('claude_monitor_smart.SmartClaudeMonitor.run_original_monitor')
    def test_main_test_alert_delegation(self, mock_run_original):
        """Test that --test-alert is delegated to original monitor."""
        wrapper = SmartClaudeMonitor()
        
        with patch('sys.argv', ['script', '--test-alert']):
            with patch('builtins.print'):
                wrapper.main()
                
                # Should call original monitor even if daemon running
                mock_run_original.assert_called_once_with(['--test-alert'])


if __name__ == '__main__':
    unittest.main()