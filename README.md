# Claude Session Monitor

**⚠️ macOS Application** - Developed and tested for macOS systems

**Code Authors:** Gemini 2.5 Pro & Claude Code
**Human Role:** Screenshots + Requirements

As a human, I don't know what the code looks like and I'm completely not interested in it. The tool should simply do what I need. This is also a "state of mind" that one needs to mature to ;)

## History

https://www.linkedin.com/posts/daniel-roziecki_znajomy-powiedzia%C5%82-mi-%C5%BCe-do-tego-trzeba-activity-7343537196462714881-tFat?utm_source=share&utm_medium=member_desktop&rcm=ACoAABpT_LwBUuuTch-E_kBfdujLPQlgPP-m_HI (PL Only)

A friend told me that you need the right mindset for this, and I think he's right.

3 days ago, someone shared a link to a cool app on GitHub (Claude Token Monitor). While I really liked the idea itself, it turned out that its operating philosophy wasn't the best for me + I was missing certain information.

So... I took a screenshot. I fired up Gemini 2.5 Pro.

I uploaded the image, described what the app does and what I wanted it to do, and after 30 minutes, after a few iterations, I have a working script that does exactly what I need.

It shows me how many sessions are left until the end of the subscription, how much money I would spend on tokens if I didn't have the Max subscription, how much time is left until the end of the actual 5-hour window (because that's how the Max subscription works - you have 50 five-hour sessions per month). It sends me notifications 30 minutes before the window ends and when nothing happens for 10 minutes (after all, it has to pay for itself :) ).

And these are all elements that the original app didn't have.

So I took a great idea and with a model (based on a screenshot and my description) in 30 minutes, 100% customized it for myself.

Yes, such things are no longer just in the Era ;)

Don't be afraid, experiment, keep an open mind and have fun with it.

## Overview

A Python-based real-time monitoring tool for Claude Code Max Sessions usage, costs, and session limits. Displays a terminal-based dashboard with progress bars showing token consumption and time remaining in active sessions.

**Inspired by:** [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) - I liked the concept but needed a different technical implementation, so I created my own version.

## Requirements

- **macOS** (optimized for macOS notifications, but runs on other platforms)
- **Python 3.9+** (uses `zoneinfo` from standard library)
- **ccusage CLI tool** - Required for fetching Claude API usage data
- **uv** - Package manager (recommended for development workflow)

## Installation

### Quick Setup (Copy & Execute)

```bash
# 1. Install ccusage (required)
curl -fsSL https://raw.githubusercontent.com/ryoppippi/ccusage/main/install.sh | sh

# 2. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Clone and setup project
git clone https://github.com/emssik/claude-session-monitor.git
cd claude-session-monitor
uv venv

# 4. Install daemon service (macOS)
./scripts/install_cron.sh

# 5. Optional: Install better notifications (macOS)
brew install terminal-notifier

# 6. Setup Claude Code hooks (optional - MANUAL STEP)
chmod +x hooks/activity_hook.py
chmod +x hooks/stop_hook.py
# Add to ~/.claude/settings.json:
# {
#   "hooks": {
#     "PreToolUse": {
#       "executable": "/absolute/path/to/claude-session-monitor/hooks/activity_hook.py"
#     },
#     "Stop": {
#       "executable": "/absolute/path/to/claude-session-monitor/hooks/stop_hook.py"
#     }
#   }
# }

# 7. Run client (auto-detects subscription by default)
uv run python3 claude_client.py
```

### Method 1: Complete System (Recommended)

1. **Install ccusage** following instructions at: https://github.com/ryoppippi/ccusage

2. **Install uv package manager:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Clone and setup:**
   ```bash
   git clone https://github.com/emssik/claude-session-monitor.git
   cd claude-session-monitor
   uv venv
   ```

4. **Install daemon service (macOS):**
   ```bash
   ./scripts/install_cron.sh
   ```

5. **Run client (automatically detects subscription):**
   ```bash
   uv run python3 claude_client.py
   ```

### Method 2: Legacy Single Script

1. **Install ccusage** following instructions at: https://github.com/ryoppippi/ccusage

2. **Download the script:**
   ```bash
   curl -O https://raw.githubusercontent.com/emssik/claude-session-monitor/main/claude_monitor.py
   ```

3. **Run directly:**
   ```bash
   python3 claude_monitor.py --start-day 15
   ```

### Optional: Enhanced Notifications (macOS)
```bash
brew install terminal-notifier
```

## What It Shows

The monitor displays:
- **Automatic subscription detection** - intelligently detects Claude Max, Pro, or pay-per-use plans
- **Current tokens used** in active sessions
- **Maximum tokens reached** during the billing period
- **Percentage of monthly limit utilized** based on detected subscription type
- **Real-time session tracking** with time remaining
- **Cost tracking** for current and maximum usage
- **macOS notifications** for time warnings and inactivity alerts
- **Anti-flicker terminal UI** for smooth monitoring experience
- **Compressed footer** with optimized information density
- **Activity sessions display** with Claude Code hooks integration
- **Smart status detection** (ACTIVE, WAITING_FOR_USER, IDLE, INACTIVE)
- **Audio signals** for session status changes

## Usage and Options

```bash
python3 claude_monitor.py --help
usage: claude_monitor.py [-h] [--start-day START_DAY] [--recalculate] [--test-alert] [--timezone TIMEZONE] [--version]

Claude Session Monitor - Monitor Claude API token and cost usage.

options:
  -h, --help            show this help message and exit
  --start-day START_DAY
                        Day of the month the billing period starts.
  --recalculate         Forces re-scanning of history to update
                        stored values (max tokens and costs).
  --test-alert          Sends a test system notification (macOS only) and exits.
  --timezone TIMEZONE   Timezone for display (e.g., 'America/New_York', 'UTC', 'Asia/Tokyo'). Default: Europe/Warsaw
  --version             Show version information and exit.
```

### Examples

```bash
# Basic usage
python3 claude_monitor.py

# Custom billing start day (15th of each month)
python3 claude_monitor.py --start-day 15

# Force recalculation of historical data
python3 claude_monitor.py --recalculate

# Test notifications (macOS only)
python3 claude_monitor.py --test-alert

# Use different timezone (default is Europe/Warsaw)
python3 claude_monitor.py --timezone UTC
python3 claude_monitor.py --timezone America/New_York
python3 claude_monitor.py --timezone Asia/Tokyo
```

## Configuration

The tool automatically creates and manages configuration in `~/.config/claude-monitor/config.json`. This file stores:

- Historical maximum token and cost values
- User preferences (billing start day)
- Session tracking data
- Alert settings

### Key Configuration Constants

You can modify these values in the source code:

- `TOTAL_MONTHLY_SESSIONS = 50` - Expected monthly session limit
- `TIME_REMAINING_ALERT_MINUTES = 30` - Warning threshold for session end
- `INACTIVITY_ALERT_MINUTES = 10` - Notification for idle periods
- `LOCAL_TZ = ZoneInfo("Europe/Warsaw")` - Default display timezone (can be overridden with --timezone)
- `ACTIVITY_SESSION_CLEANUP_HOURS = 5` - Auto-cleanup after billing window
- `HOOK_LOG_FILE_PATTERN = "claude_activity.log"` - Single log file without date stamps
- `MAX_EVENTS_PER_SESSION = 20` - Event storage limit per session for compression
- `MAX_HOOK_LOG_ENTRIES = 50` - Target size after hook log compression  
- `HOOK_LOG_COMPRESSION_THRESHOLD = 100` - Trigger compression when log exceeds this size

### Claude Code Hooks Integration (Optional)

For enhanced monitoring of active Claude Code sessions, you can configure Claude Code hooks to track real-time activity alongside billing sessions:

1. **Automatic setup via settings.json:**
   ```json
   {
     "hooks": {
       "PreToolUse": {
         "executable": "/absolute/path/to/claude-session-monitor/hooks/activity_hook.py"
       },
       "Stop": {
         "executable": "/absolute/path/to/claude-session-monitor/hooks/stop_hook.py"
       }
     }
   }
   ```
   Add this to your `~/.claude/settings.json` file (create if it doesn't exist).

2. **Make hook scripts executable:**
   ```bash
   chmod +x hooks/activity_hook.py
   chmod +x hooks/stop_hook.py
   ```

3. **What hooks provide:**
   - **Activity Sessions**: Project-based session tracking grouped by directory name
   - **Smart Status Detection**: ACTIVE, WAITING_FOR_USER, IDLE, INACTIVE based on timing
   - **Real-time Monitoring**: See current Claude Code work sessions with uptime display
   - **Audio Signals**: Double beeps for status changes (SSH-compatible)
   - **Project Grouping**: Sessions organized by project name instead of session ID

4. **Available Hook Scripts:**
   - `hooks/activity_hook.py` - Captures PreToolUse events (activity signals)
   - `hooks/stop_hook.py` - Handles Stop events (session completion)
   - `hooks/notification_hook.py` - Legacy notification hook (still supported)

5. **Activity Session Display:**
   ```
   Activity Sessions:
   🔵 my-project     - (15:23) ACTIVE
   ⏳ other-project  - (02:45) WAITING_FOR_USER
   💤 old-project    - (45:12) IDLE
   ```

**Note:** Hooks are completely optional. The monitor provides full functionality without them, tracking billing sessions via ccusage. When hooks are configured, you get additional real-time activity monitoring.

## Quick Start: Daemon + Client Architecture

### 🚀 Recommended: Auto-Installation
```bash
# Install daemon service and run client (auto-detects subscription)
./scripts/install_cron.sh
uv run python3 claude_client.py
```

### 🎯 Manual Testing (Two Terminals)

**Terminal 1 - Start Daemon:**
```bash
uv run python3 run_daemon.py --start-day 15  # Auto-detects subscription, custom billing day
```

**Terminal 2 - Start Client:**
```bash
uv run python3 claude_client.py  # Auto-detects subscription type
```

### ⚙️ Configuration Options
```bash
# Daemon with auto-detection (default) and custom settings
uv run python3 run_daemon.py --start-day 15 --time-alert 45

# Daemon with manual session limits (disable auto-detection)
uv run python3 run_daemon.py --no-auto-detect --sessions 100 --start-day 15

# Client with manual session limits
uv run python3 claude_client.py --no-auto-detect --sessions 50

# Check if daemon is running
ps aux | grep claude_daemon

# Legacy single-script mode
uv run python3 claude_monitor.py --start-day 15
```

## How It Works

**Current Architecture (Daemon + Client):**
- **Daemon Service**: Background service with cron-based installation
- **Data Collection**: Calls `ccusage blocks -j` every 10 seconds with robust error handling
- **Activity Monitoring**: Optional Claude Code hooks integration for real-time session tracking
- **Execution Strategy**: Multi-tier fallback system (wrapper script → subprocess → os.system)
- **File Storage**: Atomic writes to `~/.config/claude-monitor/monitor_data.json`
- **iCloud Sync**: Automatic synchronization to iCloud Drive for iOS widget access
- **Client Display**: Anti-flicker terminal UI with activity sessions and compressed footer
- **Notification System**: Rate-limited alerts with message-specific tracking and audio signals
- **Thread Safety**: Event-based synchronization prevents race conditions
- **Hook Integration**: Project-based activity session grouping with smart status detection
- **Log Compression**: Automatic hook log compression prevents unbounded file growth
- **Memory Optimization**: Event storage limits and size-based compression triggers

**Legacy Mode:**
- **Direct**: Original `claude_monitor.py` calls `ccusage` on every refresh (still available)

**Key Improvements:**
- **Strategy Pattern**: Unified ccusage execution with automatic fallback
- **Thread-Safe Operations**: Event-based synchronization replaces busy waiting
- **UI Enhancements**: Anti-flicker system and professional terminal appearance
- **Notification Management**: Spam prevention with configurable rate limits
- **Data Reliability**: Atomic file operations and graceful error handling

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

Inspired by [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) by Maciek-roboblog.
