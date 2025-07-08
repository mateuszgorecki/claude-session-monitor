# Claude Activity Log Format Specification

## Overview

The `claude_activity.log` file is a system-wide log that tracks Claude Code activity events. It's designed to be consumed by multiple applications and services for monitoring, analytics, and integration purposes.

## File Location

**Standard Path**: `/tmp/claude-monitor/claude_activity.log`

**Environment Override**: Set `CLAUDE_ACTIVITY_LOG_FILE` to customize the path.

**Access**: World-readable file in system temporary directory, accessible by all services.

## File Format

### Structure
- **Format**: JSON Lines (JSONL) - each line contains one JSON object
- **Encoding**: UTF-8
- **Line Terminator**: Unix newline (`\n`)
- **Atomic Writes**: Thread-safe logging with file locking

### Log Entry Schema

Each log entry is a JSON object with the following required fields:

```json
{
  "timestamp": "2025-07-08T10:30:15.123456+00:00",
  "project_name": "my-project",
  "session_id": "session_abc123",
  "event_type": "notification",
  "data": {
    "message": "Task completed successfully",
    "title": "Claude Code",
    "transcript_path": "/path/to/conversation.jsonl"
  }
}
```

## Field Specifications

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | String | ISO 8601 datetime with timezone (UTC recommended) |
| `project_name` | String | Project name derived from working directory basename |
| `session_id` | String | Unique identifier for the Claude session |
| `event_type` | String | Type of event (see Event Types below) |
| `data` | Object | Event-specific data payload |

### Timestamp Formats

Supported timestamp formats (parser handles multiple variants):

```
2025-07-08T10:30:15.123456Z           # UTC with Z suffix
2025-07-08T10:30:15.123456+00:00      # UTC with offset
2025-07-08T10:30:15+02:00             # Timezone offset
2025-07-08T10:30:15Z                  # Without microseconds
```

**Recommendation**: Use UTC timezone with explicit offset for consistency across systems.

## Event Types

### 1. Notification Events

**Event Type**: `"notification"`

**Description**: Generated when Claude Code sends notifications (user interactions, completions, waiting states)

**Data Fields**:
```json
{
  "message": "string",           // Notification message content
  "title": "string",             // Usually "Claude Code"
  "transcript_path": "string"    // Path to conversation file
}
```

**Example**:
```json
{
  "timestamp": "2025-07-08T10:30:15.123456+00:00",
  "project_name": "web-scraper",
  "session_id": "session_xyz789",
  "event_type": "notification",
  "data": {
    "message": "Waiting for user input",
    "title": "Claude Code",
    "transcript_path": "/Users/dev/.claude/conversations/session_xyz789.jsonl"
  }
}
```

### 2. Stop Events

**Event Type**: `"stop"`

**Description**: Generated when Claude sessions end (normal termination or user exit)

**Data Fields**:
```json
{
  "stop_type": "string",         // "stop" or "subagent_stop"
  "transcript_path": "string",   // Path to conversation file
  "stop_hook_active": "boolean"  // Whether this is a subagent stop
}
```

**Example**:
```json
{
  "timestamp": "2025-07-08T10:35:22.987654+00:00",
  "project_name": "web-scraper",
  "session_id": "session_xyz789",
  "event_type": "stop",
  "data": {
    "stop_type": "stop",
    "transcript_path": "/Users/dev/.claude/conversations/session_xyz789.jsonl",
    "stop_hook_active": false
  }
}
```

## File Management

### Lifecycle
- **Creation**: File is created automatically when first event is logged
- **Rotation**: File is truncated (not deleted) after cleanup periods
- **Retention**: Configurable retention period (default: 30 days)
- **Size Limits**: Configurable maximum file size (default: 10MB)

### Permissions
- **Read**: All users and processes can read the file
- **Write**: Only Claude Code hooks should write to this file
- **Directory**: `/tmp/claude-monitor/` created with appropriate permissions

### Concurrency
- **Thread Safety**: Multiple processes can write simultaneously
- **Atomic Operations**: Each log entry is written atomically
- **File Locking**: Prevents corruption during concurrent access

## Integration Guidelines

### Reading the Log

**Python Example**:
```python
import json
from datetime import datetime
from typing import Dict, Any, List

def read_activity_log(log_path: str = "/tmp/claude-monitor/claude_activity.log") -> List[Dict[str, Any]]:
    """Read and parse claude_activity.log entries."""
    events = []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    event = json.loads(line)
                    # Validate required fields
                    required_fields = ['timestamp', 'project_name', 'session_id', 'event_type', 'data']
                    if all(field in event for field in required_fields):
                        events.append(event)
                    else:
                        print(f"Warning: Invalid event at line {line_num}, missing fields")
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON at line {line_num}")
                    
    except FileNotFoundError:
        print(f"Log file not found: {log_path}")
    
    return events

def get_active_sessions(events: List[Dict[str, Any]]) -> List[str]:
    """Extract currently active session IDs from events."""
    active_sessions = set()
    
    for event in events:
        if event['event_type'] == 'notification':
            active_sessions.add(event['session_id'])
        elif event['event_type'] == 'stop':
            active_sessions.discard(event['session_id'])
    
    return list(active_sessions)
```

### Shell/Command Line Access

**Recent Events**:
```bash
tail -f /tmp/claude-monitor/claude_activity.log | jq '.'
```

**Filter by Event Type**:
```bash
cat /tmp/claude-monitor/claude_activity.log | jq 'select(.event_type == "notification")'
```

**Active Sessions**:
```bash
cat /tmp/claude-monitor/claude_activity.log | jq -r '.session_id' | sort | uniq
```

### Real-time Monitoring

**File Watching**:
```python
import time
import os

def watch_activity_log(log_path: str, callback):
    """Watch for new log entries and call callback for each new event."""
    if not os.path.exists(log_path):
        print(f"Log file does not exist: {log_path}")
        return
    
    with open(log_path, 'r') as f:
        # Start from end of file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if line:
                try:
                    event = json.loads(line.strip())
                    callback(event)
                except json.JSONDecodeError:
                    pass
            else:
                time.sleep(0.1)
```

## Error Handling

### Common Issues

1. **File Not Found**: Log file doesn't exist until first event
2. **Permission Denied**: Check directory permissions
3. **Invalid JSON**: Corrupted log entries should be skipped
4. **Missing Fields**: Validate required fields before processing

### Graceful Degradation

Applications should handle:
- Missing log file (empty state)
- Corrupted entries (skip invalid lines)
- Partial events (validate before processing)
- File rotation (detect and handle file truncation)

## Version Compatibility

**Format Version**: 1.0
**Backward Compatibility**: New fields may be added, existing fields are stable
**Migration**: Applications should ignore unknown fields for forward compatibility

## Related Documentation

- [Claude Code Hooks Configuration](https://docs.anthropic.com/claude-code)
- [Session Activity Tracking](../src/daemon/session_activity_tracker.py)
- [Hook Implementation Examples](../hooks/)

## Support

For integration questions or format clarifications, refer to:
- Project documentation in [CLAUDE.md](../CLAUDE.md)
- Hook implementation examples in [hooks/](../hooks/)
- Test cases in [tests/](../tests/)