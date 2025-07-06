#!/bin/bash
# Uninstall daemon from cron

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Claude Monitor Daemon - Cron Uninstallation ===${NC}"
echo

# Stop daemon if running
if pgrep -f "run_daemon.py" > /dev/null; then
    PID=$(pgrep -f "run_daemon.py")
    echo -e "${YELLOW}[INFO]${NC} Stopping daemon (PID: $PID)..."
    pkill -f "run_daemon.py"
    sleep 2
    echo -e "${GREEN}[SUCCESS]${NC} Daemon stopped"
else
    echo -e "${BLUE}[INFO]${NC} Daemon is not running"
fi

# Remove from crontab
echo -e "${BLUE}[INFO]${NC} Removing from crontab..."
crontab -l 2>/dev/null | grep -v "claude-session-monitor" | crontab - || true
echo -e "${GREEN}[SUCCESS]${NC} Removed from crontab"

# Remove runner script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RUNNER_SCRIPT="$PROJECT_DIR/daemon_runner.sh"

if [[ -f "$RUNNER_SCRIPT" ]]; then
    rm -f "$RUNNER_SCRIPT"
    echo -e "${GREEN}[SUCCESS]${NC} Removed runner script"
fi

echo
echo -e "${GREEN}=== Uninstallation Complete ===${NC}"
echo
echo "The daemon has been stopped and removed from cron."
echo "Your data files are preserved in ~/.config/claude-monitor/"
echo