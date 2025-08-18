# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based Claude API token usage monitor that provides real-time tracking of token consumption, costs, and 5-hour window limits based on Anthropic's official billing structure. The tool displays a terminal-based dashboard showing progress bars for 5-hour window usage, automatic subscription plan detection, and activity session tracking with an elegant emoji-enhanced interface.

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
   - `hook_log_parser.py` - Parses Claude Code hook events from JSON logs
   - `session_activity_tracker.py` - Manages activity sessions with smart status detection

2. **Client Interface** (`src/client/`)
   - `data_reader.py` - File-based data access with caching
   - `display_manager.py` - Terminal UI with 5-hour window system, emoji interface, subscription plan detection, and graceful fallback
   - `claude_client.py` - Main client with daemon detection

3. **Shared Infrastructure** (`src/shared/`)
   - `data_models.py` - SessionData, MonitoringData, ConfigData, ActivitySessionData classes
   - `file_manager.py` - Atomic file operations with iCloud sync
   - `constants.py` - Configuration constants including 5-hour window system and subscription plans
   - `utils.py` - Common utilities including window calculations and subscription plan detection
   - `hook_log_compressor.py` - Automatic hook log file compression to prevent unbounded growth
   - `project_models.py` - ProjectInfo and ProjectCache classes for intelligent project name caching
   - `git_resolver.py` - Git repository detection and project name extraction
   - `project_name_resolver.py` - Core project name resolution with cache-first approach and adaptive learning
   - `performance_metrics.py` - Cache performance monitoring and hit/miss ratio tracking
   - `memory_manager.py` - LRU-based cache cleanup and memory management

4. **Claude Code Hooks** (`hooks/`)
   - `notification_hook.py` - Captures PreToolUse events (activity signals)
   - `stop_hook.py` - Captures Stop events (session completion)
   - `activity_hook.py` - Alternative to notification_hook for activity events
   - `hook_utils.py` - Shared utilities including `get_project_name_cached()` function

### Data Flow

1. **Daemon Collection**: Background service calls `ccusage blocks -j` every 10 seconds
2. **Billing Period Filtering**: Filters sessions to current billing period using `billing_start_day`
3. **Activity Session Tracking**: Reads Claude Code hook logs from `/tmp/claude-monitor/claude_activity.log`
4. **File Storage**: Saves data to `~/.config/claude-monitor/monitor_data.json` with atomic writes
5. **iCloud Sync**: Automatically syncs to `~/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor/`
6. **Client Display**: Terminal client reads cached data for instant UI updates
7. **Widget Access**: iOS widget accesses data via iCloud Drive synchronization

## Development Commands

### Package Management
- **Python Package Manager**: Uses `uv` instead of pip for dependency management
- **Virtual Environment**: `uv venv` and `uv pip install`
- **Global Installation**: `uv tool install .` to install `ccmonitor` command globally
- **Testing**: `uv run python -m pytest` (308 tests total including integration tests)

### Running the System

```bash
# Global Installation (Recommended) - New 5h Window System
uv tool install .  # Install ccmonitor command globally
ccmonitor  # Run with automatic subscription plan detection and 5h window display

# Daemon + Client Architecture - New 5h Window System
./scripts/install_cron.sh  # Install daemon service via cron
uv run python3 claude_client.py  # Run client with 5h windows and plan detection

# Daemon (5h window system enabled by default)
uv run python3 run_daemon.py  # With automatic subscription detection

# Legacy session-based fallback available if 5h window system fails

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

### Claude Code Hooks Configuration
- **Settings File**: `~/.claude/settings.json` - Configure PreToolUse and Stop hooks
- **Hook Scripts**: Must be executable with absolute paths in settings
- **Log Location**: `/tmp/claude-monitor/claude_activity.log` (see [Activity Log Documentation](docs/claude_activity_log.md))
- **Optional Feature**: System works without hooks - graceful degradation

### Key Constants (`src/shared/constants.py`)
- `WINDOW_DURATION_HOURS = 5` - 5-hour window duration based on Anthropic's billing structure
- `SUBSCRIPTION_PLANS` - Pro ($20/mo: 10-40 prompts), Max 5x ($100/mo: 50-200), Max 20x ($200/mo: 200-800)
- `TOTAL_MONTHLY_SESSIONS = 50` - Legacy fallback session limit
- `TIME_REMAINING_ALERT_MINUTES = 30` - Warning threshold for session end
- `INACTIVITY_ALERT_MINUTES = 10` - Notification for idle periods
- `DEFAULT_CCUSAGE_FETCH_INTERVAL_SECONDS = 10` - Data collection frequency
- `ICLOUD_CONTAINER_ID = "com~apple~CloudDocs"` - iCloud sync path
- `HOOK_LOG_FILE_PATTERN = "claude_activity.log"` - Single log file without date stamps
- `ACTIVITY_SESSION_CLEANUP_HOURS = 5` - Auto-cleanup after billing window
- `MAX_EVENTS_PER_SESSION = 20` - Event storage limit per session for compression
- `MAX_HOOK_LOG_ENTRIES = 50` - Target size after hook log compression
- `HOOK_LOG_COMPRESSION_THRESHOLD = 100` - Trigger compression when log exceeds this size
- `DEFAULT_PROJECT_CACHE_FILE = "project_cache.json"` - Project name cache storage
- `MAX_CACHE_ENTRIES = 1000` - Maximum cached projects before cleanup
- `MIN_CACHE_RETENTION_HOURS = 24` - Minimum cache entry retention time

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

### Daemon Restart Considerations
- If you want to restart the daemon, just kill it and within 60 seconds the cron script will automatically restart it with correct parameters - do not manually start it

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

### Claude Code Hooks Integration
- **Hook Events**: PreToolUse → activity events, Stop → session completion
- **File Communication**: Hooks write to log files, daemon reads them (loose coupling)
- **Smart Status Detection**: Time-based algorithm (stop <2min = WAITING_FOR_USER, 2-30min = IDLE, >30min = INACTIVE)
- **Project-Based Grouping**: Sessions grouped by project_name (basename of cwd) not session_id
- **Single Log File**: `/tmp/claude-monitor/claude_activity.log` without date stamps, auto-cleanup after 5h window (see [Activity Log Documentation](docs/claude_activity_log.md))
- **Audio Signals**: Double beeps for activity status changes using osascript → afplay → terminal bell fallback
- **Project Name Caching**: Intelligent project identification using git repository detection, cache-first approach with adaptive learning, and symlink compatibility layer for /tmp storage requirements

### Display Architecture
- **Activity Sessions**: Separate from billing sessions with configurable verbosity (minimal/normal/verbose)
- **Dynamic Alignment**: Column width based on longest project name for perfect alignment
- **Anti-flicker System**: Intelligent screen refresh - clear only when sessions change, reposition otherwise
- **Status Icons**: 🔵 ACTIVE, ⏳ WAITING_FOR_USER, 💤 IDLE, ⛔ INACTIVE/STOPPED
- **Time Display**: Active sessions show uptime (mm:ss), inactive show time since last event

### Testing Strategy
- **TDD Approach**: RED-GREEN-REFACTOR cycles for all components
- **Standard Library Only**: No external test dependencies, uses unittest framework
- **Comprehensive Coverage**: 308 tests including unit, integration, and lifecycle tests
- **Integration Testing**: Full session lifecycle testing covering active sessions → cleanup → waiting → new session transitions
- **Backward Compatibility**: Automated testing ensures all changes maintain compatibility with existing interfaces
- **Error Handling**: Comprehensive error scenario testing for graceful degradation

### Data Storage Optimization
- **Hook Log Compression**: Automatic compression prevents unbounded log file growth
- **Event Storage Limits**: Sessions limited to 20 events each with automatic compression
- **Size-Based Triggers**: Compression activates when log exceeds 100 entries
- **Retention Strategy**: Keeps most recent 50 entries after compression
- **Memory Efficiency**: Prevents large hook log files from consuming excessive disk space
- **Performance Optimization**: Reduces file I/O overhead for large activity logs

### Subscription Auto-Detection (Default Behavior)
- **Automatic Detection**: Analyzes ccusage data patterns to determine subscription type (enabled by default)
- **Pattern Analysis**: Examines session durations, cost structures, and usage patterns
- **Multiple Subscription Support**: Handles Claude Max (50 sessions), Pro Enterprise (100+), and pay-per-use (1000+ limit)
- **Detection Methods**: Long session analysis, cost structure analysis, usage pattern recognition
- **Confidence Levels**: High/medium/low confidence ratings based on data quality
- **Fallback Strategy**: Defaults to Claude Max (50 sessions) when detection fails
- **CLI Control**: `--no-auto-detect` flag to disable and use manual `--sessions` values

### Recent Enhancements (Phase 7 - 5-Hour Window System)
- **5-Hour Window System**: Complete replacement of monthly session tracking with Anthropic's official 5-hour window billing structure
- **Subscription Plan Detection**: Automatic detection of Pro ($20/mo), Max 5x ($100/mo), and Max 20x ($200/mo) plans with intelligent prompt limit configuration
- **Emoji-Enhanced Interface**: Modern UI with ⏰ 5h Windows, 🔥 Current window, 📅 Started date, and 💰 Cost display
- **Billing Period Integration**: Accurate window calculations based on real subscription periods rather than fixed monthly estimates
- **Graceful Fallback**: Seamless degradation to legacy session display if 5-hour window system encounters errors
- **Real-time Window Tracking**: Dynamic progress bars showing remaining windows and current window prompt usage
- **Plan-Aware Limits**: Automatic configuration of prompt limits per window based on detected subscription plan
- **Comprehensive Window Utilities**: New utility functions for window calculations, plan detection, and current window analysis