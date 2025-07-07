#!/usr/bin/env python3
"""
Claude Code Activity Hook

This script is called by Claude Code before tool use to indicate session activity.
It reads the tool use data from stdin and logs it to a file for
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


def parse_activity_data(stdin_input: str) -> Optional[Dict[str, Any]]:
    """Parse activity data from stdin JSON input.
    
    Args:
        stdin_input: JSON string from stdin
        
    Returns:
        Parsed activity data or None if invalid
    """
    try:
        return json.loads(stdin_input.strip())
    except json.JSONDecodeError:
        return None


def create_activity_event(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an activity event from PreToolUse data.
    
    Args:
        activity_data: Parsed activity data from Claude Code
        
    Returns:
        Activity event formatted for logging
    """
    # Get project name from current working directory
    project_name = os.path.basename(os.getcwd())
    
    return {
        'project_name': project_name,
        'session_id': activity_data.get('session_id', 'unknown'),
        'event_type': 'activity',
        'data': {
            'tool_name': activity_data.get('tool_name', ''),
            'tool_parameters': activity_data.get('parameters', {}),
            'transcript_path': activity_data.get('transcript_path', '')
        }
    }


def main():
    """Main function that processes stdin and logs activity events."""
    # Read activity data from stdin
    stdin_input = sys.stdin.read()
    
    # Parse the activity data
    activity_data = parse_activity_data(stdin_input)
    if not activity_data:
        return  # Skip logging if data is invalid
    
    # Get log file path from environment or use default
    log_file = os.environ.get('CLAUDE_ACTIVITY_LOG_FILE')
    if not log_file:
        # Default log file - single file, no date suffix
        hooks_dir = os.path.expanduser('~/.config/claude-monitor/hooks')
        log_file = os.path.join(hooks_dir, 'claude_activity.log')
    
    # Create activity event
    activity_event = create_activity_event(activity_data)
    
    # Log the event
    logger = HookLogger(log_file)
    logger.log_event(activity_event)


if __name__ == '__main__':
    main()