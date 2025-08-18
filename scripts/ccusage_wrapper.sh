#!/bin/bash
# Wrapper script for ccusage that sets up proper environment
# This is a generic version - users should copy to ccusage_wrapper.sh.local and customize

# Try to find ccusage in common locations
CCUSAGE_CMD=""

# Check if ccusage is in PATH
if command -v ccusage &> /dev/null; then
    CCUSAGE_CMD="ccusage"
elif [[ -f "$HOME/.nvm/current/bin/ccusage" ]]; then
    CCUSAGE_CMD="$HOME/.nvm/current/bin/ccusage"
elif [[ -f "/usr/local/bin/ccusage" ]]; then
    CCUSAGE_CMD="/usr/local/bin/ccusage"
elif [[ -f "/opt/homebrew/bin/ccusage" ]]; then
    CCUSAGE_CMD="/opt/homebrew/bin/ccusage"
else
    # Try to find Node.js and ccusage in common nvm locations
    for NODE_VERSION in "$HOME"/.nvm/versions/node/*/bin/ccusage; do
        if [[ -f "$NODE_VERSION" ]]; then
            CCUSAGE_CMD="$NODE_VERSION"
            break
        fi
    done
fi

if [[ -z "$CCUSAGE_CMD" ]]; then
    echo "Error: ccusage not found. Please install ccusage or customize this script." >&2
    exit 1
fi

# Execute ccusage with all arguments
exec "$CCUSAGE_CMD" "$@"