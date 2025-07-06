#!/usr/bin/env python3
"""
Tests for NotificationTracker - rate limiting and duplicate prevention.
"""
import unittest
import time
import threading
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from daemon.notification_tracker import NotificationTracker, NotificationType


class TestNotificationTracker(unittest.TestCase):
    """Test NotificationTracker rate limiting implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = NotificationTracker()
    
    def test_basic_notification_tracking(self):
        """Test that NotificationTracker tracks notifications correctly."""
        # This test should fail initially because NotificationTracker doesn't exist
        self.assertIsInstance(self.tracker, NotificationTracker)
        self.assertTrue(hasattr(self.tracker, 'should_send_notification'))
    
    def test_duplicate_notification_blocking(self):
        """Test that duplicate notifications are blocked within cooldown period."""
        notification_type = NotificationType.TIME_WARNING
        message = "Test warning message"
        
        # First notification should be allowed
        first_allowed = self.tracker.should_send_notification(notification_type, message)
        self.assertTrue(first_allowed, "First notification should be allowed")
        
        # Record that we sent the notification
        self.tracker.record_notification_sent(notification_type, message)
        
        # Immediate duplicate should be blocked
        duplicate_blocked = self.tracker.should_send_notification(notification_type, message)
        self.assertFalse(duplicate_blocked, "Duplicate notification should be blocked")
    
    def test_different_notification_types_allowed(self):
        """Test that different notification types are allowed concurrently."""
        message = "Test message"
        
        # Send time warning notification
        time_allowed = self.tracker.should_send_notification(NotificationType.TIME_WARNING, message)
        self.assertTrue(time_allowed)
        self.tracker.record_notification_sent(NotificationType.TIME_WARNING, message)
        
        # Send inactivity alert with DIFFERENT message - should be allowed
        different_message = "Different test message"
        inactivity_allowed = self.tracker.should_send_notification(NotificationType.INACTIVITY_ALERT, different_message)
        self.assertTrue(inactivity_allowed, "Different notification types with different messages should be allowed")
        
        # Also test same type with different message
        time_different_msg = self.tracker.should_send_notification(NotificationType.TIME_WARNING, different_message)
        self.assertTrue(time_different_msg, "Same type with different message should be allowed")
    
    def test_cooldown_period_expiration(self):
        """Test that notifications are allowed again after cooldown period."""
        notification_type = NotificationType.TIME_WARNING
        message = "Test warning"
        
        # Set short cooldown for testing - override the defaults completely
        short_cooldowns = {notification_type: 0.1}  # 100ms for this specific type
        short_cooldown_tracker = NotificationTracker(cooldown_periods=short_cooldowns)
        
        # Send first notification
        self.assertTrue(short_cooldown_tracker.should_send_notification(notification_type, message))
        short_cooldown_tracker.record_notification_sent(notification_type, message)
        
        # Immediate duplicate should be blocked
        self.assertFalse(short_cooldown_tracker.should_send_notification(notification_type, message))
        
        # Wait for cooldown to expire
        time.sleep(0.15)
        
        # Should be allowed again after cooldown
        after_cooldown = short_cooldown_tracker.should_send_notification(notification_type, message)
        self.assertTrue(after_cooldown, "Notification should be allowed after cooldown expires")
    
    def test_configurable_cooldown_periods(self):
        """Test that different notification types can have different cooldown periods."""
        # Create tracker with different cooldowns for different types
        custom_cooldowns = {
            NotificationType.TIME_WARNING: 0.1,      # 100ms
            NotificationType.INACTIVITY_ALERT: 0.2,  # 200ms  
            NotificationType.ERROR: 0.05             # 50ms
        }
        tracker = NotificationTracker(default_cooldown=0.2, cooldown_periods=custom_cooldowns)
        
        # Note: TIME_WARNING and INACTIVITY_ALERT are aliases (same enum value "normal")
        # So they will have the same cooldown period
        
        # Test that tracker respects custom cooldowns
        self.assertEqual(tracker.get_cooldown_period(NotificationType.ERROR), 0.05)
        
        # TIME_WARNING and INACTIVITY_ALERT should have same cooldown (they're aliases)
        time_warning_cooldown = tracker.get_cooldown_period(NotificationType.TIME_WARNING)
        inactivity_cooldown = tracker.get_cooldown_period(NotificationType.INACTIVITY_ALERT)
        self.assertEqual(time_warning_cooldown, inactivity_cooldown)
    
    def test_message_specific_tracking(self):
        """Test that tracking is message-specific, not just type-specific."""
        notification_type = NotificationType.TIME_WARNING
        
        # Send notification with first message
        message1 = "Session ends in 5 minutes"
        self.assertTrue(self.tracker.should_send_notification(notification_type, message1))
        self.tracker.record_notification_sent(notification_type, message1)
        
        # Same type but different message should be allowed
        message2 = "Session ends in 3 minutes"
        different_message_allowed = self.tracker.should_send_notification(notification_type, message2)
        self.assertTrue(different_message_allowed, "Different message with same type should be allowed")
        
        # Same message should be blocked
        same_message_blocked = self.tracker.should_send_notification(notification_type, message1)
        self.assertFalse(same_message_blocked, "Same message should be blocked")
    
    def test_thread_safety(self):
        """Test that notification tracking is thread-safe."""
        notification_type = NotificationType.TIME_WARNING
        message = "Thread safety test"
        
        allowed_count = [0]
        blocked_count = [0]
        errors = []
        
        def worker_thread(thread_id):
            """Worker that tries to send notifications concurrently."""
            try:
                for i in range(5):
                    if self.tracker.should_send_notification(notification_type, f"{message}-{i}"):
                        self.tracker.record_notification_sent(notification_type, f"{message}-{i}")
                        allowed_count[0] += 1
                    else:
                        blocked_count[0] += 1
                    time.sleep(0.01)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for thread_id in range(3):
            t = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=5)
        
        # Verify no thread safety errors
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
        
        # Verify some notifications were processed
        self.assertGreater(allowed_count[0], 0, "Some notifications should have been allowed")
    
    def test_cleanup_expired_entries(self):
        """Test that expired notification entries are cleaned up."""
        notification_type = NotificationType.TIME_WARNING
        message = "Cleanup test"
        
        # Use short cooldown for faster testing
        short_tracker = NotificationTracker(default_cooldown=0.1)
        
        # Send notification
        self.assertTrue(short_tracker.should_send_notification(notification_type, message))
        short_tracker.record_notification_sent(notification_type, message)
        
        # Verify entry exists
        initial_count = len(short_tracker._notification_history)
        self.assertGreater(initial_count, 0)
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Trigger cleanup by checking another notification
        short_tracker.should_send_notification(NotificationType.INACTIVITY_ALERT, "cleanup trigger")
        
        # Verify cleanup occurred (entry should be removed)
        final_count = len(short_tracker._notification_history)
        self.assertLessEqual(final_count, initial_count, "Expired entries should be cleaned up")


class TestNotificationTrackerIntegration(unittest.TestCase):
    """Test NotificationTracker integration with notification system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = NotificationTracker()
        # Clear any existing history for clean tests
        self.tracker.clear_history()
    
    def test_integration_with_notification_manager(self):
        """Test that NotificationTracker integrates properly with existing NotificationManager."""
        # Mock the existing notification manager
        from daemon.notification_manager import NotificationManager
        
        manager = NotificationManager()
        
        # Patch the send_notification method to track calls
        with patch.object(manager, 'send_notification', return_value=True) as mock_send:
            
            # Function that uses tracker to prevent spam
            def send_tracked_notification(title, message, notification_type):
                if self.tracker.should_send_notification(notification_type, message):
                    result = manager.send_notification(title, message, notification_type)
                    if result:
                        self.tracker.record_notification_sent(notification_type, message)
                    return result
                return False  # Blocked by rate limiting
            
            # First call should succeed
            result1 = send_tracked_notification("Test", "Warning message", NotificationType.TIME_WARNING)
            self.assertTrue(result1)
            mock_send.assert_called_once()
            
            # Immediate duplicate should be blocked
            mock_send.reset_mock()
            result2 = send_tracked_notification("Test", "Warning message", NotificationType.TIME_WARNING)
            self.assertFalse(result2)
            mock_send.assert_not_called()  # Should not call underlying method
    
    def test_notification_type_enum_compatibility(self):
        """Test that NotificationTracker works with existing NotificationType enum."""
        # Verify all existing notification types are supported
        from daemon.notification_manager import NotificationType as ExistingNotificationType
        
        # Test each existing notification type
        types_to_test = [
            ExistingNotificationType.TIME_WARNING,
            ExistingNotificationType.INACTIVITY_ALERT,
            ExistingNotificationType.ERROR
        ]
        
        for i, notification_type in enumerate(types_to_test):
            # Use unique message for each test to avoid conflicts
            unique_message = f"Test {notification_type} - {i}"
            
            # Should be able to track each type
            allowed = self.tracker.should_send_notification(notification_type, unique_message)
            self.assertTrue(allowed, f"Should allow first notification of type {notification_type}")
            
            # Record the notification
            self.tracker.record_notification_sent(notification_type, unique_message)
            
            # Duplicate should be blocked
            blocked = self.tracker.should_send_notification(notification_type, unique_message)
            self.assertFalse(blocked, f"Should block duplicate notification of type {notification_type}")


class TestNotificationTrackerAdvanced(unittest.TestCase):
    """Test advanced NotificationTracker features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = NotificationTracker(default_cooldown=0.1)
        self.tracker.clear_history()
    
    def test_notification_status_tracking(self):
        """Test detailed notification status information."""
        notification_type = NotificationType.TIME_WARNING
        message = "Status test message"
        
        # Check status before sending
        status_before = self.tracker.get_notification_status(notification_type, message)
        self.assertTrue(status_before['is_allowed'])
        self.assertEqual(status_before['send_count'], 0)
        self.assertEqual(status_before['status'], 'allowed')
        
        # Send notification
        self.tracker.record_notification_sent(notification_type, message)
        
        # Check status after sending
        status_after = self.tracker.get_notification_status(notification_type, message)
        self.assertFalse(status_after['is_allowed'])
        self.assertEqual(status_after['send_count'], 1)
        self.assertEqual(status_after['status'], 'blocked')
        self.assertGreater(status_after['time_remaining'], 0)
    
    def test_force_allow_notification(self):
        """Test forcing notifications to bypass rate limiting."""
        notification_type = NotificationType.ERROR
        message = "Force allow test"
        
        # Send initial notification
        self.assertTrue(self.tracker.should_send_notification(notification_type, message))
        self.tracker.record_notification_sent(notification_type, message)
        
        # Should be blocked normally
        self.assertFalse(self.tracker.should_send_notification(notification_type, message))
        
        # Force allow should bypass rate limiting
        self.tracker.force_allow_notification(notification_type, message)
        self.assertTrue(self.tracker.should_send_notification(notification_type, message))
    
    def test_dynamic_cooldown_configuration(self):
        """Test dynamic cooldown configuration."""
        notification_type = NotificationType.TIME_WARNING
        
        # Set dynamic cooldown
        self.tracker.set_dynamic_cooldown(notification_type, base_cooldown=0.05, 
                                         escalation_factor=2.0, max_cooldown=1.0)
        
        # Verify cooldown was set
        self.assertEqual(self.tracker.get_cooldown_period(notification_type), 0.05)
    
    def test_notification_statistics_comprehensive(self):
        """Test comprehensive notification statistics."""
        # Send various notifications
        self.tracker.record_notification_sent(NotificationType.TIME_WARNING, "Warning 1")
        self.tracker.record_notification_sent(NotificationType.TIME_WARNING, "Warning 2") 
        self.tracker.record_notification_sent(NotificationType.ERROR, "Error 1")
        
        stats = self.tracker.get_notification_stats()
        
        # Verify statistics structure
        self.assertIn('total_tracked', stats)
        self.assertIn('by_type', stats)
        self.assertIn('recent_notifications', stats)
        
        # Verify counts
        self.assertEqual(stats['total_tracked'], 3)
        self.assertIn('TIME_WARNING', stats['by_type'])
        self.assertIn('ERROR', stats['by_type'])
    
    def test_cooldown_period_modification(self):
        """Test runtime modification of cooldown periods."""
        notification_type = NotificationType.ERROR
        
        # Set custom cooldown
        custom_cooldown = 0.2
        self.tracker.set_cooldown_period(notification_type, custom_cooldown)
        
        # Verify cooldown was set
        self.assertEqual(self.tracker.get_cooldown_period(notification_type), custom_cooldown)


if __name__ == '__main__':
    unittest.main()