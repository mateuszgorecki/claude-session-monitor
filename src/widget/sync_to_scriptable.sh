#!/bin/bash

# Sync Claude Monitor data to Scriptable iCloud container
# This script copies monitor_data.json from the daemon's iCloud location
# to Scriptable's iCloud Documents folder for widget access

set -e

# Paths
SOURCE_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor"
DEST_DIR="$HOME/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents/claude-monitor"
SOURCE_FILE="$SOURCE_DIR/monitor_data.json"
DEST_FILE="$DEST_DIR/monitor_data.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Claude Monitor → Scriptable Sync"
echo "================================="

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${RED}Error: Source file not found: $SOURCE_FILE${NC}"
    echo "Make sure the Claude Monitor daemon is running and syncing to iCloud."
    exit 1
fi

# Create destination directory if it doesn't exist
if [ ! -d "$DEST_DIR" ]; then
    echo -e "${YELLOW}Creating Scriptable claude-monitor directory...${NC}"
    mkdir -p "$DEST_DIR"
fi

# Check file age (should be recent if daemon is running)
if [ -f "$SOURCE_FILE" ]; then
    # Get file age in seconds
    if [[ "$OSTYPE" == "darwin"* ]]; then
        FILE_AGE=$(($(date +%s) - $(stat -f %m "$SOURCE_FILE")))
    else
        FILE_AGE=$(($(date +%s) - $(stat -c %Y "$SOURCE_FILE")))
    fi
    
    if [ $FILE_AGE -gt 300 ]; then  # 5 minutes
        echo -e "${YELLOW}Warning: Data file is $(($FILE_AGE / 60)) minutes old. Daemon might not be running.${NC}"
    fi
fi

# Copy the file
echo -e "${GREEN}Copying monitor data to Scriptable...${NC}"
cp "$SOURCE_FILE" "$DEST_FILE"

# Force iCloud sync by touching the file to trigger upload
touch "$DEST_FILE"

# Verify copy
if [ -f "$DEST_FILE" ]; then
    echo -e "${GREEN}✓ Successfully synced to Scriptable container${NC}"
    echo "File location: $DEST_FILE"
    
    # Show file info
    echo ""
    echo "File details:"
    ls -la "$DEST_FILE"
    
    # Show data preview
    echo ""
    echo "Data preview (last update):"
    if command -v jq >/dev/null 2>&1; then
        jq -r '.last_update' "$DEST_FILE" 2>/dev/null || echo "Could not parse last_update field"
    else
        grep -o '"last_update":"[^"]*"' "$DEST_FILE" | head -1 || echo "Could not find last_update field"
    fi
else
    echo -e "${RED}✗ Failed to copy file${NC}"
    exit 1
fi

echo ""
echo "Next steps:"
echo "1. Open Scriptable app on your iOS device"
echo "2. The widget should now be able to read the data file"
echo "3. Add the widget to your home screen"
echo ""
echo "To keep data in sync, run this script periodically or add it to a cron job:"
echo "  # Run every 5 minutes"
echo "  */5 * * * * $0"
echo ""
echo "Note: iCloud sync between macOS and iOS may take a few minutes."
echo "If widget shows old data, try forcing iCloud sync on iOS:"
echo "  1. Open Files app → Browse → iCloud Drive"
echo "  2. Pull down to refresh"
echo "  3. Navigate to claude-monitor folder and wait for sync"
