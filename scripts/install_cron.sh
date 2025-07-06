#!/bin/bash
# Install daemon using cron instead of launchd

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Claude Monitor Daemon - Cron Installation ===${NC}"
echo

# First, stop and remove launchd daemon if exists
DAEMON_NAME="com.claude.monitor.daemon"
PLIST_PATH="$HOME/Library/LaunchAgents/$DAEMON_NAME.plist"

if launchctl list | grep -q "$DAEMON_NAME"; then
    echo -e "${YELLOW}[INFO]${NC} Stopping existing launchd daemon..."
    launchctl bootout "gui/$(id -u)" "$PLIST_PATH" || true
    sleep 2
fi

if [[ -f "$PLIST_PATH" ]]; then
    echo -e "${YELLOW}[INFO]${NC} Removing launchd plist..."
    rm -f "$PLIST_PATH"
fi

# Create daemon runner script
RUNNER_SCRIPT="$PROJECT_DIR/daemon_runner.sh"
echo -e "${BLUE}[INFO]${NC} Creating daemon runner script..."

cat > "$RUNNER_SCRIPT" << EOF
#!/bin/bash
# Claude Monitor Daemon Runner
# This script ensures only one instance of daemon is running

# Check if daemon is already running
if pgrep -f "run_daemon.py" > /dev/null; then
    # Daemon is running, exit silently
    exit 0
fi

# Set up environment
export PATH="$PATH"
export HOME="$HOME"

# Change to project directory
cd "$PROJECT_DIR"

# Start daemon in background
echo "[\$(date)] Starting Claude Monitor daemon..." >> ~/.config/claude-monitor/cron.log

# Run daemon with nohup to detach from cron
nohup python3 run_daemon.py \\
    --start-day 17 \\
    --interval 10 \\
    --time-alert 30 \\
    --inactivity-alert 10 \\
    --sessions 50 \\
    --timezone Europe/Warsaw \\
    >> ~/.config/claude-monitor/daemon.log 2>&1 &

echo "[\$(date)] Daemon started with PID \$!" >> ~/.config/claude-monitor/cron.log
EOF

chmod +x "$RUNNER_SCRIPT"
echo -e "${GREEN}[SUCCESS]${NC} Runner script created"

# Add to crontab
echo -e "${BLUE}[INFO]${NC} Adding to crontab..."

# Remove any existing claude-monitor entries
crontab -l 2>/dev/null | grep -v "claude-session-monitor" | crontab - || true

# Add new cron job (every minute)
(crontab -l 2>/dev/null; echo "* * * * * $RUNNER_SCRIPT") | crontab -

echo -e "${GREEN}[SUCCESS]${NC} Cron job installed"

# Create log directory if not exists
mkdir -p ~/.config/claude-monitor

# Start daemon immediately
echo -e "${BLUE}[INFO]${NC} Starting daemon now..."
"$RUNNER_SCRIPT"

sleep 3

# Check if daemon is running
if pgrep -f "run_daemon.py" > /dev/null; then
    PID=$(pgrep -f "run_daemon.py")
    echo -e "${GREEN}[SUCCESS]${NC} Daemon is running (PID: $PID)"
else
    echo -e "${RED}[ERROR]${NC} Daemon failed to start"
    echo -e "${YELLOW}[INFO]${NC} Check logs at: ~/.config/claude-monitor/daemon.log"
    exit 1
fi

echo
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo
echo "Daemon is now running and will:"
echo "  • Monitor Claude usage every 10 seconds"
echo "  • Auto-restart if it crashes (checked every minute by cron)"
echo "  • Save data to ~/.config/claude-monitor/monitor_data.json"
echo
echo "Useful commands:"
echo "  • Check if running:  ps aux | grep run_daemon.py"
echo "  • View logs:         tail -f ~/.config/claude-monitor/daemon.log"
echo "  • View cron logs:    tail -f ~/.config/claude-monitor/cron.log"
echo "  • Stop daemon:       pkill -f run_daemon.py"
echo "  • Remove from cron:  crontab -e  # remove claude-session-monitor line"
echo