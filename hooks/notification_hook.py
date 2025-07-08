#!/usr/bin/env python3
"""
Claude Code Notification Hook

This script is called by Claude Code when notifications are sent.
It reads the notification data from stdin and logs it to a file for
the session monitor daemon to process.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path so we can import hooks module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hooks.hook_utils import HookLogger


def parse_notification_data(stdin_input: str) -> Optional[Dict[str, Any]]:
    """Parse notification data from stdin JSON input.
    
    Args:
        stdin_input: JSON string from stdin
        
    Returns:
        Parsed notification data or None if invalid
    """
    try:
        return json.loads(stdin_input.strip())
    except json.JSONDecodeError:
        return None


def create_activity_event(notification_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an activity event from notification data.
    
    Args:
        notification_data: Parsed notification data from Claude Code
        
    Returns:
        Activity event formatted for logging
    """
    # Get project name from current working directory
    project_name = os.path.basename(os.getcwd())
    
    return {
        'project_name': project_name,
        'session_id': notification_data.get('session_id', 'unknown'),
        'event_type': 'notification',
        'data': {
            'message': notification_data.get('message', ''),
            'title': notification_data.get('title', ''),
            'transcript_path': notification_data.get('transcript_path', '')
        }
    }


def main():
    """Main function that processes stdin and logs notification events."""
    # Read notification data from stdin
    stdin_input = sys.stdin.read()
    
    # Parse the notification data
    notification_data = parse_notification_data(stdin_input)
    if not notification_data:
        return  # Skip logging if data is invalid
    
    # Get log file path from environment or use default
    log_file = os.environ.get('CLAUDE_ACTIVITY_LOG_FILE')
    if not log_file:
        # Default log file - single file, no date suffix
        hooks_dir = '/tmp/claude-monitor'
        log_file = os.path.join(hooks_dir, 'claude_activity.log')
    
    # Create activity event
    activity_event = create_activity_event(notification_data)
    
    # Log the event
    logger = HookLogger(log_file)
    logger.log_event(activity_event)


if __name__ == '__main__':
    main()