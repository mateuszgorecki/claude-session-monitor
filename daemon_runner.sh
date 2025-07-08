#!/bin/bash
# Claude Monitor Daemon Runner
# This script ensures only one instance of daemon is running

# Check if daemon is already running
if pgrep -f "run_daemon.py" > /dev/null; then
    # Daemon is running, exit silently
    exit 0
fi

# Set up environment
export PATH="/Users/daniel/.codeium/windsurf/bin:/opt/homebrew/opt/openssh/bin:/usr/local/opt/openssl@3/bin:/opt/homebrew/opt/libpq/bin:/Users/daniel/.nvm/versions/node/v20.5.0/bin:/Users/daniel/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/opt/local/bin:/opt/local/sbin:/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/daniel/.asdf/shims/:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/Library/Apple/usr/bin:/Users/daniel/Library/Application Support/JetBrains/Toolbox/scripts"
export HOME="/Users/daniel"

# Change to project directory
cd "/Users/daniel/00_work/projects/tools/claude-session-monitor"

# Start daemon in background
echo "[$(date)] Starting Claude Monitor daemon..." >> ~/.config/claude-monitor/cron.log

# Run daemon with nohup to detach from cron
nohup python3 run_daemon.py \
    --start-day 17 \
    --interval 10 \
    --time-alert 30 \
    --inactivity-alert 10 \
    --sessions 50 \
    --timezone Europe/Warsaw \
    >> ~/.config/claude-monitor/daemon.log 2>&1 &

echo "[$(date)] Daemon started with PID $!" >> ~/.config/claude-monitor/cron.log
