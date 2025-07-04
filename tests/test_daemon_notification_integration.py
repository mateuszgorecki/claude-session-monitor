"""Tests for daemon integration with NotificationManager"""
import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from daemon.claude_daemon import ClaudeDaemon
from daemon.notification_manager import NotificationManager, NotificationType
from shared.data_models import ConfigData, ErrorStatus, SessionData, MonitoringData
from datetime import datetime, timedelta, timezone


class TestDaemonNotificationIntegration(unittest.TestCase):
    """Test integration between daemon and notification manager"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = ConfigData(
            ccusage_fetch_interval_seconds=10,
            total_monthly_sessions=50,
            billing_start_day=1,
            time_remaining_alert_minutes=30,
            inactivity_alert_minutes=10
        )

    @patch('daemon.claude_daemon.DataCollector')
    @patch('daemon.claude_daemon.DataFileManager')
    def test_daemon_initializes_notification_manager(self, mock_file_manager, mock_data_collector):
        """Test that daemon initializes NotificationManager during setup"""
        daemon = ClaudeDaemon(self.config)
        
        # Verify notification manager is initialized
        self.assertIsInstance(daemon.notification_manager, NotificationManager)

    @patch('daemon.claude_daemon.DataCollector')
    @patch('daemon.claude_daemon.DataFileManager')
    def test_daemon_sends_error_notification_on_consecutive_failures(self, mock_file_manager, mock_data_collector):
        """Test that daemon sends error notifications after multiple failures"""
        # Set up mocks
        mock_collector_instance = MagicMock()
        mock_data_collector.return_value = mock_collector_instance
        
        # Mock consecutive failures
        error_status = ErrorStatus(
            has_error=True,
            error_message="ccusage command failed",
            error_code=1,
            consecutive_failures=6,
            last_successful_update=datetime.now() - timedelta(minutes=60)
        )
        mock_collector_instance.collect_data.side_effect = RuntimeError("ccusage failed")
        mock_collector_instance.get_error_status.return_value = error_status
        
        daemon = ClaudeDaemon(self.config)
        
        # Mock notification manager
        with patch.object(daemon.notification_manager, 'send_error_notification') as mock_notify:
            mock_notify.return_value = True
            
            # Trigger data collection
            daemon._collect_data()
            
            # Verify error notification was sent
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args[0][0]
            self.assertIn("6 consecutive failures", call_args)

    @patch('daemon.claude_daemon.DataCollector')
    @patch('daemon.claude_daemon.DataFileManager')
    def test_daemon_sends_time_warning_notification(self, mock_file_manager, mock_data_collector):
        """Test that daemon sends time warning notifications for active sessions"""
        # Set up mocks
        mock_collector_instance = MagicMock()
        mock_data_collector.return_value = mock_collector_instance
        
        # Create active session ending in 25 minutes
        now_utc = datetime.now(timezone.utc)
        end_time = now_utc + timedelta(minutes=25)
        session = SessionData(
            session_id="test-session",
            start_time=now_utc - timedelta(hours=1),
            end_time=end_time,
            total_tokens=1500,
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.15,
            is_active=True
        )
        
        monitoring_data = MonitoringData(
            current_sessions=[session],
            total_sessions_this_month=1,
            total_cost_this_month=0.15,
            max_tokens_per_session=1500,
            last_update=now_utc,
            billing_period_start=now_utc.replace(day=1),
            billing_period_end=now_utc.replace(day=28)
        )
        
        mock_collector_instance.collect_data.return_value = monitoring_data
        
        daemon = ClaudeDaemon(self.config)
        
        # Mock notification manager
        with patch.object(daemon.notification_manager, 'send_time_warning') as mock_notify:
            mock_notify.return_value = True
            
            # Trigger data collection
            daemon._collect_data()
            
            # Verify time warning was sent (approximately 25 minutes remaining)
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args[0][0]
            self.assertLess(abs(call_args - 25), 2)  # Within 2 minutes tolerance

    @patch('daemon.claude_daemon.DataCollector')
    @patch('daemon.claude_daemon.DataFileManager')
    def test_daemon_sends_inactivity_alert(self, mock_file_manager, mock_data_collector):
        """Test that daemon sends inactivity alerts for idle sessions"""
        # Set up mocks
        mock_collector_instance = MagicMock()
        mock_data_collector.return_value = mock_collector_instance
        
        # Create session that started 70 minutes ago (triggering inactivity logic)
        now_utc = datetime.now(timezone.utc)
        session = SessionData(
            session_id="test-session",
            start_time=now_utc - timedelta(minutes=70),
            end_time=now_utc + timedelta(hours=1),  # Still active
            total_tokens=1500,
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.15,
            is_active=True
        )
        
        monitoring_data = MonitoringData(
            current_sessions=[session],
            total_sessions_this_month=1,
            total_cost_this_month=0.15,
            max_tokens_per_session=1500,
            last_update=now_utc,
            billing_period_start=now_utc.replace(day=1),
            billing_period_end=now_utc.replace(day=28)
        )
        
        mock_collector_instance.collect_data.return_value = monitoring_data
        
        daemon = ClaudeDaemon(self.config)
        
        # Mock notification manager
        with patch.object(daemon.notification_manager, 'send_inactivity_alert') as mock_notify:
            mock_notify.return_value = True
            
            # Trigger data collection
            daemon._collect_data()
            
            # Verify inactivity alert was sent (for approximately 10 minutes of inactivity)
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args[0][0]
            self.assertGreater(call_args, 0)  # Some inactivity detected


if __name__ == '__main__':
    unittest.main()