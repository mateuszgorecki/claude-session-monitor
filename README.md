# Claude Session Monitor

**⚠️ macOS Application** - Developed and tested for macOS systems

A Python-based real-time monitoring tool for Claude API usage, costs, and 5-hour window limits based on Anthropic's official billing structure. Features automatic subscription plan detection and displays an elegant emoji-enhanced terminal dashboard with progress bars showing 5-hour window usage and prompt consumption.

**Inspired by:** [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor)

## Features

### 🎯 5-Hour Window System (New!)
The monitor now displays based on Anthropic's official billing structure:
- **⏰ 5h Windows** - Real-time tracking of remaining 5-hour windows in your billing period
- **🔥 Current window** - Prompt usage within the current 5-hour window
- **📅 Started date** - Clean billing period display with days remaining
- **💰 Cost tracking** - Streamlined monthly cost display

### 🤖 Automatic Plan Detection
- **Pro Plan ($20/mo)** - 10-40 prompts per 5h window (25 default)
- **Max 5x Plan ($100/mo)** - 50-200 prompts per 5h window (125 default)  
- **Max 20x Plan ($200/mo)** - 200-800 prompts per 5h window (500 default)
- **Intelligent fallback** to legacy session display if needed

### 🎨 Enhanced Interface
- **Emoji-enhanced UI** with modern visual indicators
- **Anti-flicker terminal display** for smooth monitoring
- **Dynamic progress bars** showing window usage
- **Activity sessions display** with Claude Code hooks integration
- **Smart status detection** (ACTIVE, WAITING_FOR_USER, IDLE, INACTIVE)
- **Audio signals** for session status changes
- **macOS notifications** for time warnings and inactivity alerts

## Requirements

- **macOS** (optimized for macOS notifications, but runs on other platforms)
- **Python 3.9+** (uses `zoneinfo` from standard library)
- **ccusage CLI tool** - Required for fetching Claude API usage data
- **uv** - Package manager (recommended for development workflow)

## Quick Installation

```bash
# 1. Install ccusage (required)
curl -fsSL https://raw.githubusercontent.com/ryoppippi/ccusage/main/install.sh | sh

# 2. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Clone and setup project
git clone https://github.com/mateuszgorecki/claude-session-monitor.git
cd claude-session-monitor
uv venv

# 4. Install daemon service (macOS)
./scripts/install_cron.sh

# 5. Run client (auto-detects subscription by default)
uv run python3 claude_client.py
```

## Installation Methods

### Method 1: Complete System (Recommended)

1. **Install ccusage** following instructions at: https://github.com/ryoppippi/ccusage

2. **Install uv package manager:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Clone and setup:**
   ```bash
   git clone https://github.com/mateuszgorecki/claude-session-monitor.git
   cd claude-session-monitor
   uv venv
   ```

4. **Install daemon service (macOS):**
   ```bash
   ./scripts/install_cron.sh
   ```

5. **Install globally for easy access:**
   ```bash
   uv tool install .  # Install ccmonitor command globally
   ```

6. **Run from anywhere:**
   ```bash
   ccmonitor  # 5-hour window system with automatic plan detection
   ```

   Or run locally in project directory:
   ```bash
   uv run python3 claude_client.py  # 5-hour window system
   ```

### Method 2: Legacy Single Script

1. **Install ccusage** following instructions at: https://github.com/ryoppippi/ccusage

2. **Download the script:**
   ```bash
   curl -O https://raw.githubusercontent.com/mateuszgorecki/claude-session-monitor/main/claude_monitor.py
   ```

3. **Run directly:**
   ```bash
   python3 claude_monitor.py --start-day 15
   ```

### Optional: Enhanced Notifications (macOS)
```bash
brew install terminal-notifier
```

## Usage Examples

### Basic Usage (Auto-Detection Enabled by Default)

```bash
# Run with automatic subscription detection
uv run python3 claude_client.py

# Run daemon with auto-detection
uv run python3 run_daemon.py --start-day 15

# Check daemon status
uv run python3 claude_client.py --check-daemon
```

### Manual Configuration (Disable Auto-Detection)

```bash
# Client with manual session limits
uv run python3 claude_client.py --no-auto-detect --sessions 50

# Daemon with manual limits
uv run python3 run_daemon.py --no-auto-detect --sessions 100 --start-day 15
```

### Legacy Mode Examples

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

## Command Line Options

### Client Options

```bash
usage: claude_client.py [-h] [--refresh-interval REFRESH_INTERVAL]
                        [--check-daemon] [--data-file DATA_FILE]
                        [--sessions SESSIONS] [--auto-detect]
                        [--no-auto-detect] [--version]

options:
  --refresh-interval    Display refresh interval in seconds (default: 1.0)
  --check-daemon        Check if daemon is running and exit
  --data-file          Path to daemon data file
  --sessions           Total monthly sessions limit (default: 50 for Claude Max)
  --auto-detect        Automatically detect subscription type (default: enabled)
  --no-auto-detect     Disable automatic detection and use manual --sessions
  --version            Show version information
```

### Daemon Options

```bash
usage: run_daemon.py [-h] [--start-day START_DAY] [--interval INTERVAL]
                     [--time-alert TIME_ALERT] [--sessions SESSIONS]
                     [--auto-detect] [--no-auto-detect] [--timezone TIMEZONE]

options:
  --start-day          Day of the month the billing period starts (1-31)
  --interval           Data collection interval in seconds (default: 10)
  --time-alert         Time warning threshold in minutes (default: 30)
  --sessions           Maximum monthly sessions (default: 50)
  --auto-detect        Auto-detect subscription type (default: enabled)
  --no-auto-detect     Disable auto-detection and use manual --sessions
  --timezone           Timezone for display (default: Europe/Warsaw)
```

## Architecture

### Daemon + Client Architecture (Recommended)

- **Daemon Service**: Background service with cron-based installation
- **Data Collection**: Calls `ccusage blocks -j` every 10 seconds with robust error handling
- **Automatic Subscription Detection**: Analyzes usage patterns to determine subscription type
- **File Storage**: Atomic writes to `~/.config/claude-monitor/monitor_data.json`
- **iCloud Sync**: Automatic synchronization to iCloud Drive for iOS widget access
- **Client Display**: Anti-flicker terminal UI with activity sessions
- **Notification System**: Rate-limited alerts with audio signals

### Quick Start: Daemon + Client

#### 🚀 Recommended: Auto-Installation
```bash
# Install daemon service and run client (auto-detects subscription)
./scripts/install_cron.sh
uv run python3 claude_client.py
```

#### 🎯 Manual Testing (Two Terminals)

**Terminal 1 - Start Daemon:**
```bash
uv run python3 run_daemon.py --start-day 15  # Auto-detects subscription, custom billing day
```

**Terminal 2 - Start Client:**
```bash
uv run python3 claude_client.py  # Auto-detects subscription type
```

#### ⚙️ Configuration Options
```bash
# Daemon with auto-detection (default) and custom settings
uv run python3 run_daemon.py --start-day 15 --time-alert 45

# Daemon with manual session limits (disable auto-detection)
uv run python3 run_daemon.py --no-auto-detect --sessions 100 --start-day 15

# Client with manual session limits
uv run python3 claude_client.py --no-auto-detect --sessions 50

# Check if daemon is running
ps aux | grep claude_daemon
```

## Configuration

The tool automatically creates and manages configuration in `~/.config/claude-monitor/config.json`. This file stores:

- Historical maximum token and cost values
- User preferences (billing start day)
- Session tracking data
- Alert settings

### Key Configuration Constants

You can modify these values in the source code:

- `DEFAULT_TOTAL_MONTHLY_SESSIONS = 50` - Default session limit for Claude Max
- `TIME_REMAINING_ALERT_MINUTES = 30` - Warning threshold for session end
- `INACTIVITY_ALERT_MINUTES = 10` - Notification for idle periods
- `LOCAL_TZ = ZoneInfo("Europe/Warsaw")` - Default display timezone
- `ACTIVITY_SESSION_CLEANUP_HOURS = 5` - Auto-cleanup after billing window

### Claude Code Hooks Integration (Optional)

For enhanced monitoring of active Claude Code sessions:

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
   - **Activity Sessions**: Project-based session tracking
   - **Smart Status Detection**: ACTIVE, WAITING_FOR_USER, IDLE, INACTIVE
   - **Real-time Monitoring**: See current Claude Code work sessions
   - **Audio Signals**: Double beeps for status changes
   - **Project Grouping**: Sessions organized by project name

**Note:** Hooks are completely optional. The monitor provides full functionality without them, tracking billing sessions via ccusage.

## Subscription Auto-Detection

The monitor automatically detects your Claude subscription type:

- **Claude Max**: 50 sessions per month (5-hour limit each)
- **Claude Pro Enterprise**: 100+ sessions per month  
- **Pay-per-use**: High session limits (1000+)

Detection is based on:
- Session duration patterns (5-hour limits indicate Max subscription)
- Cost structure analysis (zero costs indicate subscription vs pay-per-use)
- Usage pattern recognition

Use `--no-auto-detect --sessions N` to override automatic detection.

## iOS Widget

Copy `claude_widget.js` to Scriptable app for iOS/iPadOS widget support via iCloud sync.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

Inspired by [Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) by Maciek-roboblog.