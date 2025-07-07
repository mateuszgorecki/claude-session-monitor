#!/usr/bin/env python3
"""
Claude Code Stop Hook

This script is called by Claude Code when sessions are stopped or subagents stop.
It reads the stop data from stdin and logs it to a file for the session monitor
daemon to process.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path so we can import hooks module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hooks.hook_utils import HookLogger


def parse_stop_data(stdin_input: str) -> Optional[Dict[str, Any]]:
    """Parse stop data from stdin JSON input.
    
    Args:
        stdin_input: JSON string from stdin
        
    Returns:
        Parsed stop data or None if invalid
    """
    try:
        return json.loads(stdin_input.strip())
    except json.JSONDecodeError:
        return None


def determine_stop_type(stop_data: Dict[str, Any]) -> str:
    """Determine the type of stop event based on the data.
    
    Args:
        stop_data: Parsed stop data from Claude Code
        
    Returns:
        'stop' for normal stop, 'subagent_stop' for subagent stop
    """
    if stop_data.get('stop_hook_active', False):
        return 'subagent_stop'
    return 'stop'


def create_stop_event(stop_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a stop event from stop data.
    
    Args:
        stop_data: Parsed stop data from Claude Code
        
    Returns:
        Stop event formatted for logging
    """
    stop_type = determine_stop_type(stop_data)
    
    # Get project name from current working directory
    project_name = os.path.basename(os.getcwd())
    
    return {
        'project_name': project_name,
        'session_id': stop_data.get('session_id', 'unknown'),
        'event_type': 'stop',
        'data': {
            'stop_type': stop_type,
            'transcript_path': stop_data.get('transcript_path', ''),
            'stop_hook_active': stop_data.get('stop_hook_active', False)
        }
    }


def main():
    """Main function that processes stdin and logs stop events."""
    # Read stop data from stdin
    stdin_input = sys.stdin.read()
    
    # Parse the stop data
    stop_data = parse_stop_data(stdin_input)
    if not stop_data:
        return  # Skip logging if data is invalid
    
    # Get log file path from environment or use default
    log_file = os.environ.get('CLAUDE_ACTIVITY_LOG_FILE')
    if not log_file:
        # Default log file - single file, no date suffix
        hooks_dir = os.path.expanduser('~/.config/claude-monitor/hooks')
        log_file = os.path.join(hooks_dir, 'claude_activity.log')
    
    # Create stop event
    stop_event = create_stop_event(stop_data)
    
    # Log the event
    logger = HookLogger(log_file)
    logger.log_event(stop_event)


if __name__ == '__main__':
    main()