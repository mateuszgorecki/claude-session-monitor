#!/bin/bash
# Claude Monitor Daemon Installation Script for macOS
# This script installs the Claude monitoring daemon as a launchd service

set -e  # Exit on any error

# Script information
SCRIPT_NAME="Claude Monitor Daemon Installer"
SCRIPT_VERSION="1.0"
DAEMON_NAME="com.claude.monitor.daemon"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is designed for macOS only."
        exit 1
    fi
}

# Check if running as root (should not be)
check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root."
        log_error "Please run as a regular user - the daemon will be installed per-user."
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed."
        log_error "Please install Python 3 and try again."
        exit 1
    fi
    
    # Check for ccusage command
    if ! command -v ccusage &> /dev/null; then
        log_error "ccusage command is required but not found in PATH."
        log_error "Please install ccusage CLI tool and try again."
        log_error "See: https://github.com/anthropics/ccusage"
        exit 1
    fi
    
    # Check for uv (if available)
    if command -v uv &> /dev/null; then
        log_info "Found uv package manager - will use for Python execution"
        USE_UV=true
    else
        log_info "Using system Python 3"
        USE_UV=false
    fi
    
    log_success "All dependencies found"
}

# Get script directory
get_script_dir() {
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    log_info "Project directory: $PROJECT_DIR"
    
    # Verify project structure
    if [[ ! -f "$PROJECT_DIR/run_daemon.py" ]]; then
        log_error "Could not find run_daemon.py in project directory"
        log_error "Make sure you're running this script from the correct location"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_DIR/config/com.claude.monitor.daemon.plist" ]]; then
        log_error "Could not find plist template in config directory"
        exit 1
    fi
}

# Get user configuration
get_user_config() {
    log_info "Getting daemon configuration..."
    
    # Default values
    DEFAULT_BILLING_START_DAY=1
    DEFAULT_SESSIONS=50
    DEFAULT_TIMEZONE="Europe/Warsaw"
    
    # Prompt for billing start day
    read -p "Enter billing start day (1-31, default: $DEFAULT_BILLING_START_DAY): " BILLING_START_DAY
    BILLING_START_DAY=${BILLING_START_DAY:-$DEFAULT_BILLING_START_DAY}
    
    # Validate billing start day
    if ! [[ "$BILLING_START_DAY" =~ ^[0-9]+$ ]] || [ "$BILLING_START_DAY" -lt 1 ] || [ "$BILLING_START_DAY" -gt 31 ]; then
        log_error "Invalid billing start day. Must be between 1 and 31."
        exit 1
    fi
    
    # Prompt for monthly sessions
    read -p "Enter maximum monthly sessions (default: $DEFAULT_SESSIONS): " MONTHLY_SESSIONS
    MONTHLY_SESSIONS=${MONTHLY_SESSIONS:-$DEFAULT_SESSIONS}
    
    # Validate monthly sessions
    if ! [[ "$MONTHLY_SESSIONS" =~ ^[0-9]+$ ]] || [ "$MONTHLY_SESSIONS" -lt 1 ]; then
        log_error "Invalid monthly sessions. Must be a positive number."
        exit 1
    fi
    
    # Prompt for timezone
    read -p "Enter timezone (default: $DEFAULT_TIMEZONE): " TIMEZONE
    TIMEZONE=${TIMEZONE:-$DEFAULT_TIMEZONE}
    
    log_info "Configuration:"
    log_info "  Billing start day: $BILLING_START_DAY"
    log_info "  Monthly sessions: $MONTHLY_SESSIONS"
    log_info "  Timezone: $TIMEZONE"
}

# Setup directories
setup_directories() {
    log_info "Setting up directories..."
    
    # Create config directory
    CONFIG_DIR="$HOME/.config/claude-monitor"
    mkdir -p "$CONFIG_DIR"
    
    # Create launchd directory
    LAUNCHD_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCHD_DIR"
    
    # Create iCloud directory (if possible)
    ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor"
    if mkdir -p "$ICLOUD_DIR" 2>/dev/null; then
        log_success "Created iCloud Drive directory for widget sync"
    else
        log_warning "Could not create iCloud Drive directory - widget sync may not work"
        log_warning "You may need to enable iCloud Drive in System Preferences"
    fi
    
    log_success "Directories created"
}

# Create and install plist
install_plist() {
    log_info "Installing daemon plist..."
    
    PLIST_TEMPLATE="$PROJECT_DIR/config/com.claude.monitor.daemon.plist"
    PLIST_DEST="$LAUNCHD_DIR/$DAEMON_NAME.plist"
    
    # Create plist from template
    cp "$PLIST_TEMPLATE" "$PLIST_DEST"
    
    # Get full PATH and Python path
    FULL_PATH="$PATH"
    PYTHON_PATH=$(command -v python3)
    
    # Replace placeholders
    sed -i '' "s|__DAEMON_PATH__|$PROJECT_DIR|g" "$PLIST_DEST"
    sed -i '' "s|__USER_HOME__|$HOME|g" "$PLIST_DEST"
    sed -i '' "s|__USER_NAME__|$(whoami)|g" "$PLIST_DEST"
    sed -i '' "s|__BILLING_START_DAY__|$BILLING_START_DAY|g" "$PLIST_DEST"
    sed -i '' "s|__PYTHON_PATH__|$PYTHON_PATH|g" "$PLIST_DEST"
    sed -i '' "s|__FULL_PATH__|$FULL_PATH|g" "$PLIST_DEST"
    
    log_info "Using Python: $PYTHON_PATH"
    log_info "Using PATH: $FULL_PATH"
    
    # Update sessions count
    sed -i '' "s|<string>50</string>|<string>$MONTHLY_SESSIONS</string>|g" "$PLIST_DEST"
    
    # Update timezone
    sed -i '' "s|<string>Europe/Warsaw</string>|<string>$TIMEZONE</string>|g" "$PLIST_DEST"
    
    log_success "Plist installed at $PLIST_DEST"
}

# Test daemon execution
test_daemon() {
    log_info "Testing daemon execution..."
    
    # Create a temporary test
    cd "$PROJECT_DIR"
    
    if [[ "$USE_UV" == "true" ]]; then
        PYTHON_CMD="uv run python3"
    else
        PYTHON_CMD="python3"
    fi
    
    # Test daemon can start (quick test)
    timeout 5 $PYTHON_CMD run_daemon.py --start-day "$BILLING_START_DAY" --sessions "$MONTHLY_SESSIONS" --timezone "$TIMEZONE" || {
        if [[ $? -eq 124 ]]; then
            log_success "Daemon test completed (timeout is expected)"
        else
            log_error "Daemon test failed"
            exit 1
        fi
    }
}

# Load daemon service
load_daemon() {
    log_info "Loading daemon service..."
    
    # Stop existing daemon if running
    if launchctl list | grep -q "$DAEMON_NAME"; then
        log_info "Stopping existing daemon..."
        launchctl bootout "gui/$(id -u)" "$LAUNCHD_DIR/$DAEMON_NAME.plist" 2>/dev/null || true
    fi
    
    # Load new daemon using bootstrap (modern launchctl)
    launchctl bootstrap "gui/$(id -u)" "$LAUNCHD_DIR/$DAEMON_NAME.plist"
    
    # Wait a moment for startup
    sleep 2
    
    # Check if daemon is running
    if launchctl list | grep -q "$DAEMON_NAME"; then
        log_success "Daemon loaded and running"
    else
        log_error "Daemon failed to start"
        log_error "Check logs: $CONFIG_DIR/daemon.log"
        exit 1
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    # Check daemon status
    if launchctl list | grep -q "$DAEMON_NAME"; then
        log_success "✅ Daemon is running"
    else
        log_error "❌ Daemon is not running"
        return 1
    fi
    
    # Check data file creation (wait up to 30 seconds)
    DATA_FILE="$CONFIG_DIR/monitor_data.json"
    for i in {1..30}; do
        if [[ -f "$DATA_FILE" ]]; then
            log_success "✅ Data file created: $DATA_FILE"
            break
        fi
        sleep 1
    done
    
    if [[ ! -f "$DATA_FILE" ]]; then
        log_warning "⚠️  Data file not yet created (may take a few moments)"
    fi
    
    # Check log files
    LOG_FILE="$CONFIG_DIR/daemon.log"
    ERROR_LOG="$CONFIG_DIR/daemon.error.log"
    
    if [[ -f "$LOG_FILE" ]]; then
        log_success "✅ Log file available: $LOG_FILE"
    fi
    
    if [[ -f "$ERROR_LOG" ]] && [[ -s "$ERROR_LOG" ]]; then
        log_warning "⚠️  Error log contains data: $ERROR_LOG"
    fi
}

# Show completion message
show_completion() {
    log_success "🎉 Claude Monitor Daemon installation completed!"
    echo
    echo "=== Installation Summary ==="
    echo "• Daemon service: $DAEMON_NAME"
    echo "• Configuration: Billing day $BILLING_START_DAY, $MONTHLY_SESSIONS sessions/month"
    echo "• Data file: $CONFIG_DIR/monitor_data.json"
    echo "• Log files: $CONFIG_DIR/daemon.log"
    echo "• iCloud sync: $ICLOUD_DIR/ (if available)"
    echo
    echo "=== Next Steps ==="
    echo "• The daemon is now running and will start automatically at login"
    echo "• Use 'claude_monitor_smart.py' or 'claude_client_standalone.py' to view data"
    echo "• Check logs if you encounter issues: $CONFIG_DIR/daemon.log"
    echo "• To uninstall: run scripts/uninstall_daemon.sh"
    echo
    echo "=== Daemon Management ==="
    echo "• Stop:    launchctl bootout gui/\$(id -u) ~/Library/LaunchAgents/$DAEMON_NAME.plist"
    echo "• Start:   launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/$DAEMON_NAME.plist"
    echo "• Status:  launchctl list | grep claude.monitor"
    echo
}

# Main installation function
main() {
    echo "=== $SCRIPT_NAME v$SCRIPT_VERSION ==="
    echo
    
    # Checks
    check_macos
    check_not_root
    get_script_dir
    check_dependencies
    
    # Configuration
    get_user_config
    
    # Confirm installation
    echo
    read -p "Proceed with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled."
        exit 0
    fi
    
    # Installation steps
    setup_directories
    install_plist
    test_daemon
    load_daemon
    verify_installation
    show_completion
    
    log_success "Installation completed successfully!"
}

# Error handling
trap 'log_error "Installation failed. Check the output above for details."' ERR

# Run main function
main "$@"