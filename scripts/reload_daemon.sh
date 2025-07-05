#!/bin/bash
# Quick reload script for daemon development

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DAEMON_NAME="com.claude.monitor.daemon"
PLIST_PATH="$HOME/Library/LaunchAgents/$DAEMON_NAME.plist"

echo "Reloading Claude Monitor Daemon..."

# Stop daemon if running
if launchctl list | grep -q "$DAEMON_NAME"; then
    echo "Stopping daemon..."
    launchctl bootout "gui/$(id -u)" "$PLIST_PATH" || true
    sleep 2
fi

# Check if plist exists
if [[ ! -f "$PLIST_PATH" ]]; then
    echo "ERROR: Daemon not installed. Run install_daemon.sh first."
    exit 1
fi

# Start daemon
echo "Starting daemon..."
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"

# Check status
sleep 2
if launchctl list | grep -q "$DAEMON_NAME"; then
    echo "✅ Daemon reloaded successfully"
    echo ""
    echo "Check logs:"
    echo "  tail -f ~/.config/claude-monitor/daemon.log"
    echo "  tail -f ~/.config/claude-monitor/daemon.error.log"
else
    echo "❌ Daemon failed to start"
    echo "Check error log: ~/.config/claude-monitor/daemon.error.log"
    exit 1
fi