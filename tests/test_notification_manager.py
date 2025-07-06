"""Tests for NotificationManager class - TDD Red Phase"""
import unittest
from unittest.mock import patch, MagicMock, call
import subprocess
import logging
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from daemon.notification_manager import NotificationManager, NotificationType


class TestNotificationManager(unittest.TestCase):
    """Test cases for NotificationManager class"""

    def setUp(self):
        """Set up test fixtures"""
        self.notification_manager = NotificationManager()

    def test_initialization(self):
        """Test NotificationManager initialization"""
        nm = NotificationManager()
        self.assertIsInstance(nm, NotificationManager)
        self.assertIsNotNone(nm.logger)

    @patch('subprocess.run')
    @patch.object(NotificationManager, '_check_gui_available', return_value=True)
    def test_send_notification_with_terminal_notifier_success(self, mock_gui, mock_run):
        """Test successful notification sending using terminal-notifier"""
        # Mock successful terminal-notifier execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.notification_manager.send_notification(
            title="Test Title",
            message="Test Message",
            notification_type=NotificationType.TIME_WARNING
        )
        
        self.assertTrue(result)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        # Check if terminal-notifier executable is in the command
        self.assertTrue(any('terminal-notifier' in arg for arg in call_args))
        self.assertIn('Test Title', call_args)
        self.assertIn('Test Message', call_args)

    @patch('subprocess.run')
    @patch.object(NotificationManager, '_check_gui_available', return_value=True)
    def test_send_notification_fallback_to_osascript(self, mock_gui, mock_run):
        """Test fallback to osascript when terminal-notifier fails"""
        # Mock terminal-notifier failure, osascript success
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if any('terminal-notifier' in str(arg) for arg in cmd):
                raise FileNotFoundError("terminal-notifier not found")
            else:  # osascript
                mock_result = MagicMock()
                mock_result.returncode = 0
                return mock_result
        
        mock_run.side_effect = side_effect
        
        result = self.notification_manager.send_notification(
            title="Test Title",
            message="Test Message",
            notification_type=NotificationType.INACTIVITY_ALERT
        )
        
        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)  # terminal-notifier + osascript

    @patch('subprocess.run')
    def test_send_notification_both_methods_fail(self, mock_run):
        """Test notification failure when both methods fail"""
        # Mock both terminal-notifier and osascript failure
        mock_run.side_effect = Exception("All notification methods failed")
        
        result = self.notification_manager.send_notification(
            title="Test Title",
            message="Test Message",
            notification_type=NotificationType.ERROR
        )
        
        self.assertFalse(result)

    def test_send_time_warning_notification(self):
        """Test sending time warning notification"""
        with patch.object(self.notification_manager, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            result = self.notification_manager.send_time_warning(30)
            
            self.assertTrue(result)
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            self.assertIn("30 minutes", kwargs['message'])
            self.assertEqual(kwargs['notification_type'], NotificationType.TIME_WARNING)

    def test_send_inactivity_alert(self):
        """Test sending inactivity alert notification"""
        with patch.object(self.notification_manager, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            result = self.notification_manager.send_inactivity_alert(10)
            
            self.assertTrue(result)
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            self.assertIn("10 minutes", kwargs['message'])
            self.assertEqual(kwargs['notification_type'], NotificationType.INACTIVITY_ALERT)

    def test_send_error_notification(self):
        """Test sending error notification"""
        with patch.object(self.notification_manager, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            result = self.notification_manager.send_error_notification("Test error message")
            
            self.assertTrue(result)
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            self.assertIn("Test error message", kwargs['message'])
            self.assertEqual(kwargs['notification_type'], NotificationType.ERROR)

    @patch('subprocess.run')
    @patch.object(NotificationManager, '_check_gui_available', return_value=True)
    def test_notification_types_have_different_urgency(self, mock_gui, mock_run):
        """Test that different notification types use appropriate urgency levels"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Test ERROR notification (should be critical)
        self.notification_manager.send_notification(
            title="Error",
            message="Error message",
            notification_type=NotificationType.ERROR
        )
        
        call_args = mock_run.call_args[0][0]
        # Check for error-specific timeout parameter
        self.assertIn('-timeout', call_args)

    @patch('daemon.notification_manager.logging')
    def test_logging_on_notification_failure(self, mock_logging):
        """Test that failures are properly logged"""
        with patch('subprocess.run', side_effect=Exception("Test error")):
            result = self.notification_manager.send_notification(
                title="Test",
                message="Test message",
                notification_type=NotificationType.TIME_WARNING
            )
            
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()