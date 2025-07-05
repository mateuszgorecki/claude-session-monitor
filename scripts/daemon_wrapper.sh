#!/bin/bash
# Daemon wrapper script to ensure proper environment setup
# This script is called by launchd and sets up the environment before running the Python daemon

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load user's bash profile to get PATH and other environment variables
if [ -f "$HOME/.bash_profile" ]; then
    source "$HOME/.bash_profile"
fi

if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Load NVM if available
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    source "$NVM_DIR/nvm.sh"
fi

# Ensure PATH includes common locations
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH"

# Add Python paths
if [ -d "/opt/homebrew/opt/python@3.11/bin" ]; then
    export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"
fi

if [ -d "/opt/homebrew/opt/python@3.12/bin" ]; then
    export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"
fi

# Set other required environment variables
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
export USER="${USER:-$(whoami)}"
export HOME="${HOME:-$(eval echo ~$USER)}"

# Log environment for debugging
echo "=== Daemon Wrapper Starting ===" >> "$HOME/.config/claude-monitor/daemon.log"
echo "Date: $(date)" >> "$HOME/.config/claude-monitor/daemon.log"
echo "PATH: $PATH" >> "$HOME/.config/claude-monitor/daemon.log"
echo "USER: $USER" >> "$HOME/.config/claude-monitor/daemon.log"
echo "HOME: $HOME" >> "$HOME/.config/claude-monitor/daemon.log"
echo "ccusage location: $(which ccusage 2>/dev/null || echo 'NOT FOUND')" >> "$HOME/.config/claude-monitor/daemon.log"
echo "python3 location: $(which python3 2>/dev/null || echo 'NOT FOUND')" >> "$HOME/.config/claude-monitor/daemon.log"
echo "=========================" >> "$HOME/.config/claude-monitor/daemon.log"

# Change to project directory
cd "$PROJECT_DIR"

# Check if we should use uv
if command -v uv &> /dev/null; then
    echo "Using uv to run daemon" >> "$HOME/.config/claude-monitor/daemon.log"
    exec uv run python3 run_daemon.py "$@"
else
    echo "Using system python3 to run daemon" >> "$HOME/.config/claude-monitor/daemon.log"
    exec python3 run_daemon.py "$@"
fi