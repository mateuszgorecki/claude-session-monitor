# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based Claude API token usage monitor that provides real-time tracking of token consumption, costs, and session limits. The tool displays a terminal-based dashboard showing progress bars for token usage and time remaining in active sessions.

## Architecture

### Current Implementation (Daemon + Client Architecture)

- **Daemon Service**: `run_daemon.py` - Background service for continuous data collection
- **Client Interface**: `claude_client.py` - Terminal display reading from daemon-generated files
- **Legacy Monitor**: `claude_monitor.py` - Original monolithic implementation (still available)
- **iOS Widget**: `claude_widget.js` - Scriptable widget for iOS/iPadOS via iCloud sync
- **Installation Scripts**: `install_cron.sh` - macOS daemon installation

### Key Components

1. **Daemon Core** (`src/daemon/`)
   - `claude_daemon.py` - Main daemon class with lifecycle management
   - `data_collector.py` - ccusage integration with billing period filtering
   - `notification_manager.py` - macOS notifications (terminal-notifier + osascript)
   - `ccusage_executor.py` - Unified ccusage execution with strategy pattern and fallback
   - `improved_subprocess_pool.py` - Thread-safe subprocess management with event-based synchronization
   - `notification_tracker.py` - Rate limiting system for notification spam prevention

2. **Client Interface** (`src/client/`)
   - `data_reader.py` - File-based data access with caching
   - `display_manager.py` - Terminal UI with anti-flicker system and compressed footer
   - `claude_client.py` - Main client with daemon detection

3. **Shared Infrastructure** (`src/shared/`)
   - `data_models.py` - SessionData, MonitoringData, ConfigData classes
   - `file_manager.py` - Atomic file operations with iCloud sync
   - `constants.py` - Configuration constants
   - `utils.py` - Common utilities

### Data Flow

1. **Daemon Collection**: Background service calls `ccusage blocks -j` every 10 seconds
2. **Billing Period Filtering**: Filters sessions to current billing period using `billing_start_day`
3. **File Storage**: Saves data to `~/.config/claude-monitor/monitor_data.json` with atomic writes
4. **iCloud Sync**: Automatically syncs to `~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/`
5. **Client Display**: Terminal client reads cached data for instant UI updates
6. **Widget Access**: iOS widget accesses data via iCloud Drive synchronization

## Development Commands

### Package Management
- **Python Package Manager**: Uses `uv` instead of pip for dependency management
- **Virtual Environment**: `uv venv` and `uv pip install`
- **Testing**: `uv run python -m pytest` (87 tests total)

### Running the System

```bash
# Daemon + Client Architecture (Recommended)
./scripts/install_cron.sh  # Install daemon service via cron
uv run python3 claude_client.py  # Run client

# Legacy monolithic mode
python3 claude_monitor.py

# iOS Widget (copy to Scriptable app)
cp claude_widget.js [Scriptable Scripts folder]
```

## Dependencies

### System Requirements
- **ccusage CLI**: Must be installed and accessible in PATH
- **Python**: 3.9+ (uses `zoneinfo` from standard library)
- **macOS**: Optimized for macOS notifications and cron integration

### Python Dependencies
- **Standard Library Only**: No external Python packages required
- **Testing**: Uses built-in `unittest` framework
- **Package Manager**: `uv` for development workflow

### Platform-Specific
- **macOS Notifications**: `terminal-notifier` (preferred) or `osascript` (fallback)
- **iOS Widget**: Scriptable app from App Store
- **Daemon Installation**: cron-based process monitoring

## Configuration

### Runtime Configuration
- **Billing Start Day**: Configurable via `--start-day` parameter
- **Data Collection**: 10-second intervals (configurable in constants)
- **File Locations**: `~/.config/claude-monitor/` (local) + iCloud sync
- **Timezone**: Uses system timezone with UTC storage

### Key Constants (`src/shared/constants.py`)
- `TOTAL_MONTHLY_SESSIONS = 50` - Expected monthly session limit
- `TIME_REMAINING_ALERT_MINUTES = 30` - Warning threshold for session end
- `INACTIVITY_ALERT_MINUTES = 10` - Notification for idle periods
- `DEFAULT_CCUSAGE_FETCH_INTERVAL_SECONDS = 10` - Data collection frequency
- `ICLOUD_CONTAINER_ID = "com~apple~CloudDocs"` - iCloud sync path

## Architecture Decisions

### Daemon vs Direct Integration
- **Daemon Mode**: Background service + file-based client (recommended)
- **Direct Mode**: Original monolithic approach (fallback)
- **Smart Wrapper**: Auto-detects daemon availability and routes appropriately

### Error Handling Strategy
- **Daemon Resilience**: Continues operation despite individual failures
- **Graceful Degradation**: Returns `{"blocks": []}` on ccusage failures
- **File Operations**: Atomic writes prevent data corruption
- **Notification Failures**: Logged but don't interrupt monitoring

### macOS Cron Integration
- **Process Monitoring**: Watchdog-based installation for reliability
- **Auto-restart**: Daemon automatically restarts if crashed
- **Solution**: `install_cron.sh` uses cron + process monitoring

### Data Accuracy Critical Points
- **Billing Period Logic**: Must filter to current period, not all sessions
- **Timezone Handling**: All comparisons must use UTC-aware datetimes
- **Session Counting**: Prevent duplicates via processed_sessions tracking
- **Field Parsing**: Use correct ccusage structure (`tokenCounts.inputTokens`, `costUSD`)

### ccusage Execution Strategy
- **Strategy Pattern**: CcusageExecutor with multiple fallback strategies
- **Execution Methods**: WrapperScriptStrategy → DirectSubprocessStrategy → OSSystemStrategy
- **Fallback Mechanism**: Automatic degradation for launchd fork restrictions and path issues
- **Thread Safety**: Event-based synchronization replaces busy waiting loops

### User Interface Design
- **Anti-flicker System**: Screen clearing only on first render, cursor positioning for updates
- **Compressed Footer**: Optimized text density (saves ~18 characters per line)
- **Server Terminology**: "Server" instead of "Daemon" for clearer architecture understanding
- **Professional Icons**: 🖥️ for server services, consistent iconography

### Notification Management
- **Rate Limiting**: Message-specific tracking prevents notification spam
- **Cooldown Periods**: Configurable per-notification-type rate limits
- **Enum Compatibility**: Handles NotificationType aliases (TIME_WARNING/INACTIVITY_ALERT)
- **Thread Safety**: Concurrent notification delivery without conflicts