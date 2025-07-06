"""
Notification rate limiting and duplicate prevention.
Prevents notification spam by tracking sent notifications and enforcing cooldown periods.
"""
import time
import threading
import logging
from typing import Dict, Optional, Tuple, Any
from enum import Enum

# Import existing NotificationType for compatibility
from .notification_manager import NotificationType


class NotificationTracker:
    """
    Tracks sent notifications and prevents spam through rate limiting.
    
    Features:
    - Per-notification-type and per-message tracking
    - Configurable cooldown periods for different notification types
    - Thread-safe operations
    - Automatic cleanup of expired entries
    """
    
    def __init__(self, default_cooldown: float = 300.0, cooldown_periods: Optional[Dict[NotificationType, float]] = None):
        """
        Initialize notification tracker.
        
        Args:
            default_cooldown: Default cooldown period in seconds (5 minutes)
            cooldown_periods: Custom cooldown periods for specific notification types
        """
        self.default_cooldown = default_cooldown
        self.logger = logging.getLogger(__name__)
        
        # Thread synchronization
        self._lock = threading.Lock()
        
        # Notification history: key = (notification_type, message), value = (timestamp, count)
        self._notification_history: Dict[Tuple[NotificationType, str], Tuple[float, int]] = {}
        
        # Set up cooldown periods
        if cooldown_periods:
            # Use provided cooldown periods
            self._cooldown_periods = cooldown_periods.copy()
            self.logger.debug(f"Using custom cooldown periods: {self._cooldown_periods}")
        else:
            # Use default cooldown periods
            self._cooldown_periods = {
                NotificationType.TIME_WARNING: 300.0,      # 5 minutes
                NotificationType.INACTIVITY_ALERT: 600.0,  # 10 minutes  
                NotificationType.ERROR: 180.0              # 3 minutes
            }
            self.logger.debug(f"Using default cooldown periods: {self._cooldown_periods}")
        
        self.logger.debug(f"NotificationTracker initialized with default_cooldown={default_cooldown}s")
    
    def should_send_notification(self, notification_type: NotificationType, message: str) -> bool:
        """
        Check if a notification should be sent based on rate limiting rules.
        
        Args:
            notification_type: Type of notification
            message: Notification message content
            
        Returns:
            True if notification should be sent, False if blocked by rate limiting
        """
        with self._lock:
            # Clean up expired entries first
            self._cleanup_expired_entries()
            
            key = (notification_type, message)
            current_time = time.time()
            cooldown_period = self.get_cooldown_period(notification_type)
            
            if key in self._notification_history:
                last_sent_time, count = self._notification_history[key]
                
                # Check if cooldown period has passed
                if current_time - last_sent_time < cooldown_period:
                    self.logger.debug(f"Notification blocked by rate limiting: {notification_type.name} - {message[:50]}...")
                    return False
            
            # Notification is allowed
            self.logger.debug(f"Notification allowed: {notification_type.name} - {message[:50]}...")
            return True
    
    def record_notification_sent(self, notification_type: NotificationType, message: str):
        """
        Record that a notification was successfully sent.
        
        Args:
            notification_type: Type of notification that was sent
            message: Message content that was sent
        """
        with self._lock:
            key = (notification_type, message)
            current_time = time.time()
            
            # Update or create entry
            if key in self._notification_history:
                _, count = self._notification_history[key]
                self._notification_history[key] = (current_time, count + 1)
            else:
                self._notification_history[key] = (current_time, 1)
            
            self.logger.debug(f"Recorded notification: {notification_type.name} - {message[:50]}...")
    
    def get_cooldown_period(self, notification_type: NotificationType) -> float:
        """
        Get the cooldown period for a specific notification type.
        
        Args:
            notification_type: Type of notification
            
        Returns:
            Cooldown period in seconds
        """
        return self._cooldown_periods.get(notification_type, self.default_cooldown)
    
    def _cleanup_expired_entries(self):
        """
        Remove expired entries from notification history.
        Must be called while holding self._lock.
        """
        current_time = time.time()
        expired_keys = []
        
        for key, (timestamp, count) in self._notification_history.items():
            notification_type, message = key
            cooldown_period = self.get_cooldown_period(notification_type)
            
            if current_time - timestamp > cooldown_period:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._notification_history[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired notification entries")
    
    def get_notification_stats(self) -> Dict[str, any]:
        """
        Get statistics about tracked notifications.
        
        Returns:
            Dictionary with notification statistics
        """
        with self._lock:
            stats = {
                'total_tracked': len(self._notification_history),
                'by_type': {},
                'recent_notifications': []
            }
            
            current_time = time.time()
            
            for (notification_type, message), (timestamp, count) in self._notification_history.items():
                type_name = notification_type.name
                if type_name not in stats['by_type']:
                    stats['by_type'][type_name] = {'count': 0, 'total_sent': 0}
                
                stats['by_type'][type_name]['count'] += 1
                stats['by_type'][type_name]['total_sent'] += count
                
                # Add to recent notifications if within last hour
                if current_time - timestamp < 3600:
                    stats['recent_notifications'].append({
                        'type': type_name,
                        'message': message[:100],  # Truncate for display
                        'timestamp': timestamp,
                        'count': count,
                        'time_since': current_time - timestamp
                    })
            
            # Sort recent notifications by timestamp (newest first)
            stats['recent_notifications'].sort(key=lambda x: x['timestamp'], reverse=True)
            
            return stats
    
    def clear_history(self):
        """Clear all notification history (for testing or reset purposes)."""
        with self._lock:
            cleared_count = len(self._notification_history)
            self._notification_history.clear()
            self.logger.debug(f"Cleared {cleared_count} notification history entries")
    
    def set_cooldown_period(self, notification_type: NotificationType, cooldown_seconds: float):
        """
        Set custom cooldown period for a notification type.
        
        Args:
            notification_type: Type of notification
            cooldown_seconds: Cooldown period in seconds
        """
        with self._lock:
            self._cooldown_periods[notification_type] = cooldown_seconds
            self.logger.debug(f"Set cooldown for {notification_type.name} to {cooldown_seconds}s")
    
    def force_allow_notification(self, notification_type: NotificationType, message: str):
        """
        Force allow a notification by removing it from rate limiting history.
        Useful for high-priority notifications that should bypass rate limiting.
        
        Args:
            notification_type: Type of notification
            message: Message content
        """
        with self._lock:
            key = (notification_type, message)
            if key in self._notification_history:
                del self._notification_history[key]
                self.logger.debug(f"Forced allow notification: {notification_type.name} - {message[:50]}...")
    
    def get_notification_status(self, notification_type: NotificationType, message: str) -> Dict[str, Any]:
        """
        Get detailed status information for a specific notification.
        
        Args:
            notification_type: Type of notification
            message: Message content
            
        Returns:
            Dictionary with notification status details
        """
        with self._lock:
            key = (notification_type, message)
            current_time = time.time()
            cooldown_period = self.get_cooldown_period(notification_type)
            
            if key in self._notification_history:
                last_sent_time, count = self._notification_history[key]
                time_since_last = current_time - last_sent_time
                time_remaining = max(0, cooldown_period - time_since_last)
                
                return {
                    'notification_type': notification_type.name,
                    'message': message[:100],  # Truncated for display
                    'is_allowed': time_remaining == 0,
                    'last_sent_time': last_sent_time,
                    'time_since_last': time_since_last,
                    'cooldown_period': cooldown_period,
                    'time_remaining': time_remaining,
                    'send_count': count,
                    'status': 'blocked' if time_remaining > 0 else 'allowed'
                }
            else:
                return {
                    'notification_type': notification_type.name,
                    'message': message[:100],
                    'is_allowed': True,
                    'last_sent_time': None,
                    'time_since_last': None,
                    'cooldown_period': cooldown_period,
                    'time_remaining': 0,
                    'send_count': 0,
                    'status': 'allowed'
                }
    
    def set_dynamic_cooldown(self, notification_type: NotificationType, base_cooldown: float, 
                           escalation_factor: float = 1.5, max_cooldown: float = 3600.0):
        """
        Set dynamic cooldown that increases with repeated notifications.
        
        Args:
            notification_type: Type of notification
            base_cooldown: Base cooldown period in seconds
            escalation_factor: Factor by which cooldown increases with each repeat
            max_cooldown: Maximum cooldown period in seconds
        """
        # This could be implemented in a future version for dynamic rate limiting
        # For now, just set the base cooldown
        self.set_cooldown_period(notification_type, base_cooldown)
        self.logger.debug(f"Set dynamic cooldown for {notification_type.name}: "
                         f"base={base_cooldown}s, factor={escalation_factor}, max={max_cooldown}s")


# Global notification tracker instance
_notification_tracker = None
_tracker_lock = threading.Lock()


def get_notification_tracker() -> NotificationTracker:
    """Get or create the global notification tracker instance."""
    global _notification_tracker
    
    with _tracker_lock:
        if _notification_tracker is None:
            _notification_tracker = NotificationTracker()
        return _notification_tracker


def should_send_notification(notification_type: NotificationType, message: str) -> bool:
    """
    Convenience function to check if notification should be sent.
    
    Args:
        notification_type: Type of notification
        message: Message content
        
    Returns:
        True if notification should be sent, False if rate limited
    """
    tracker = get_notification_tracker()
    return tracker.should_send_notification(notification_type, message)


def record_notification_sent(notification_type: NotificationType, message: str):
    """
    Convenience function to record that a notification was sent.
    
    Args:
        notification_type: Type of notification
        message: Message content
    """
    tracker = get_notification_tracker()
    tracker.record_notification_sent(notification_type, message)