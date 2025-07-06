"""NotificationManager for macOS system notifications"""
import subprocess
import logging
import os
from enum import Enum
from typing import Optional


class NotificationType(Enum):
    """Types of notifications with different urgency levels"""
    TIME_WARNING = "normal"
    INACTIVITY_ALERT = "normal" 
    ERROR = "critical"


class NotificationManager:
    """Manages system notifications on macOS using terminal-notifier or osascript fallback"""
    
    def __init__(self):
        """Initialize notification manager"""
        self.logger = logging.getLogger(__name__)
        self._gui_available = None  # Cache GUI availability check
    
    def send_notification(self, title: str, message: str, notification_type: NotificationType) -> bool:
        """
        Send a system notification using available macOS notification methods
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification affecting urgency
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            # Check if GUI is available before attempting notifications
            if not self._check_gui_available():
                self.logger.warning("GUI not available, skipping notification")
                return False
            
            # Try terminal-notifier first (more feature-rich)
            if self._send_via_terminal_notifier(title, message, notification_type):
                return True
            
            # Fallback to osascript
            return self._send_via_osascript(title, message)
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return False
    
    def _check_gui_available(self) -> bool:
        """
        Check if GUI is available for notifications.
        
        Returns:
            bool: True if GUI is available, False otherwise
        """
        if self._gui_available is not None:
            return self._gui_available
        
        try:
            # Check if we have a display
            if not os.environ.get('DISPLAY'):
                self.logger.debug("No DISPLAY environment variable set")
                self._gui_available = False
                return False
            
            # Test basic GUI access with a lightweight command
            result = subprocess.run(
                ['osascript', '-e', 'return "GUI test"'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self._gui_available = True
                self.logger.debug("GUI access confirmed")
                return True
            else:
                self.logger.warning(f"GUI access test failed: {result.stderr}")
                self._gui_available = False
                return False
                
        except Exception as e:
            self.logger.warning(f"GUI availability check failed: {e}")
            self._gui_available = False
            return False
    
    def _send_via_terminal_notifier(self, title: str, message: str, notification_type: NotificationType) -> bool:
        """
        Send notification using terminal-notifier command
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type affecting urgency level
            
        Returns:
            bool: True if successful, False if terminal-notifier unavailable
        """
        import os
        
        try:
            # Try application bundle path first (required for launchd)
            terminal_notifier_paths = [
                '/Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier',
                '/usr/local/bin/terminal-notifier',
                '/opt/homebrew/bin/terminal-notifier'
            ]
            
            terminal_notifier_path = None
            for path in terminal_notifier_paths:
                if os.path.exists(path):
                    terminal_notifier_path = path
                    break
            
            if not terminal_notifier_path:
                self.logger.warning("terminal-notifier not found in any expected location")
                return False
            
            cmd = [
                terminal_notifier_path,
                '-title', title,
                '-message', message,
                '-sound', 'default'
            ]
            
            # Add urgency level based on notification type
            if notification_type == NotificationType.ERROR:
                cmd.extend(['-timeout', '10'])  # Longer timeout for errors
                # Use critical urgency for errors
                cmd.extend(['-execute', 'echo "critical notification"'])
            
            # Set up environment for GUI access
            env = os.environ.copy()
            env.update({
                'PATH': '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin',
                'HOME': os.path.expanduser('~'),
                'LANG': 'en_US.UTF-8',
                'DISPLAY': ':0',
                'USER': os.getenv('USER', 'unknown'),
                'TMPDIR': '/tmp'
            })
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            return result.returncode == 0
            
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # terminal-notifier not available or timeout
            return False
        except Exception as e:
            self.logger.warning(f"terminal-notifier failed: {e}")
            return False
    
    def _send_via_osascript(self, title: str, message: str) -> bool:
        """
        Send notification using osascript (AppleScript) as fallback
        
        Args:
            title: Notification title
            message: Notification message
            
        Returns:
            bool: True if successful, False otherwise
        """
        import os
        
        try:
            # AppleScript to display notification
            script = f'''
            display notification "{message}" with title "{title}" sound name "default"
            '''
            
            # Set up environment for GUI access
            env = os.environ.copy()
            env.update({
                'PATH': '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin',
                'HOME': os.path.expanduser('~'),
                'LANG': 'en_US.UTF-8',
                'DISPLAY': ':0',
                'USER': os.getenv('USER', 'unknown'),
                'TMPDIR': '/tmp'
            })
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"osascript notification failed: {e}")
            return False
    
    def send_time_warning(self, minutes_remaining: int) -> bool:
        """
        Send a time warning notification
        
        Args:
            minutes_remaining: Minutes until session ends
            
        Returns:
            bool: True if notification sent successfully
        """
        title = "Claude Session Warning"
        message = f"Your Claude session will end in {minutes_remaining} minutes. Save your work!"
        
        return self.send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.TIME_WARNING
        )
    
    def send_inactivity_alert(self, minutes_inactive: int) -> bool:
        """
        Send an inactivity alert notification
        
        Args:
            minutes_inactive: Minutes since last activity
            
        Returns:
            bool: True if notification sent successfully
        """
        title = "Claude Session Inactive"
        message = f"Your Claude session has been inactive for {minutes_inactive} minutes."
        
        return self.send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.INACTIVITY_ALERT
        )
    
    def send_error_notification(self, error_message: str) -> bool:
        """
        Send an error notification
        
        Args:
            error_message: Description of the error
            
        Returns:
            bool: True if notification sent successfully
        """
        title = "Claude Monitor Error"
        message = f"Error in Claude monitoring: {error_message}"
        
        return self.send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.ERROR
        )