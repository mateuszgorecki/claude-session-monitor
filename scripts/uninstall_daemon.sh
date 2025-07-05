#!/bin/bash
# Claude Monitor Daemon Uninstallation Script for macOS
# This script removes the Claude monitoring daemon and associated files

set -e  # Exit on any error

# Script information
SCRIPT_NAME="Claude Monitor Daemon Uninstaller"
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
        log_error "Please run as a regular user."
        exit 1
    fi
}

# Check daemon status
check_daemon_status() {
    if launchctl list | grep -q "$DAEMON_NAME"; then
        DAEMON_RUNNING=true
        log_info "Daemon is currently running"
    else
        DAEMON_RUNNING=false
        log_info "Daemon is not currently running"
    fi
    
    PLIST_PATH="$HOME/Library/LaunchAgents/$DAEMON_NAME.plist"
    if [[ -f "$PLIST_PATH" ]]; then
        DAEMON_INSTALLED=true
        log_info "Daemon plist found at: $PLIST_PATH"
    else
        DAEMON_INSTALLED=false
        log_info "Daemon plist not found - may not be installed"
    fi
}

# Stop daemon service
stop_daemon() {
    if [[ "$DAEMON_RUNNING" == "true" ]]; then
        log_info "Stopping daemon service..."
        
        if launchctl unload "$PLIST_PATH" 2>/dev/null; then
            log_success "Daemon stopped successfully"
        else
            log_warning "Failed to stop daemon (it may already be stopped)"
        fi
        
        # Wait for daemon to stop
        sleep 2
        
        # Verify daemon is stopped
        if launchctl list | grep -q "$DAEMON_NAME"; then
            log_error "Daemon is still running after unload attempt"
            log_error "You may need to restart your computer to fully stop it"
        else
            log_success "Daemon confirmed stopped"
        fi
    else
        log_info "Daemon is not running - skipping stop"
    fi
}

# Remove daemon plist
remove_plist() {
    if [[ "$DAEMON_INSTALLED" == "true" ]]; then
        log_info "Removing daemon plist..."
        
        if rm -f "$PLIST_PATH"; then
            log_success "Daemon plist removed"
        else
            log_error "Failed to remove daemon plist"
            exit 1
        fi
    else
        log_info "Daemon plist not found - skipping removal"
    fi
}

# Get user preference for data cleanup
get_cleanup_preference() {
    echo
    log_info "Data cleanup options:"
    echo "  1. Keep all data files (recommended)"
    echo "  2. Remove daemon logs only"
    echo "  3. Remove all daemon data (logs + monitoring data)"
    echo "  4. Remove everything (logs + data + config)"
    echo
    
    while true; do
        read -p "Choose cleanup option (1-4, default: 1): " -n 1 -r CLEANUP_OPTION
        echo
        CLEANUP_OPTION=${CLEANUP_OPTION:-1}
        
        case $CLEANUP_OPTION in
            1|2|3|4)
                break
                ;;
            *)
                log_error "Invalid option. Please choose 1-4."
                ;;
        esac
    done
    
    case $CLEANUP_OPTION in
        1)
            log_info "Selected: Keep all data files"
            REMOVE_LOGS=false
            REMOVE_DATA=false
            REMOVE_CONFIG=false
            ;;
        2)
            log_info "Selected: Remove daemon logs only"
            REMOVE_LOGS=true
            REMOVE_DATA=false
            REMOVE_CONFIG=false
            ;;
        3)
            log_info "Selected: Remove logs and monitoring data"
            REMOVE_LOGS=true
            REMOVE_DATA=true
            REMOVE_CONFIG=false
            ;;
        4)
            log_info "Selected: Remove everything"
            REMOVE_LOGS=true
            REMOVE_DATA=true
            REMOVE_CONFIG=true
            ;;
    esac
}

# Remove data files based on user preference
cleanup_data() {
    CONFIG_DIR="$HOME/.config/claude-monitor"
    ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor"
    
    if [[ "$REMOVE_LOGS" == "true" ]]; then
        log_info "Removing daemon logs..."
        
        # Remove log files
        rm -f "$CONFIG_DIR/daemon.log"
        rm -f "$CONFIG_DIR/daemon.error.log"
        
        log_success "Daemon logs removed"
    fi
    
    if [[ "$REMOVE_DATA" == "true" ]]; then
        log_info "Removing monitoring data..."
        
        # Remove data files
        rm -f "$CONFIG_DIR/monitor_data.json"
        rm -f "$CONFIG_DIR/config.json"
        
        # Remove iCloud data if it exists
        if [[ -f "$ICLOUD_DIR/monitor_data.json" ]]; then
            rm -f "$ICLOUD_DIR/monitor_data.json"
            log_success "iCloud monitoring data removed"
        fi
        
        log_success "Monitoring data removed"
    fi
    
    if [[ "$REMOVE_CONFIG" == "true" ]]; then
        log_info "Removing configuration directory..."
        
        # Remove entire config directory
        if [[ -d "$CONFIG_DIR" ]]; then
            rm -rf "$CONFIG_DIR"
            log_success "Configuration directory removed"
        fi
        
        # Remove iCloud directory if empty or if user wants full cleanup
        if [[ -d "$ICLOUD_DIR" ]]; then
            if rmdir "$ICLOUD_DIR" 2>/dev/null; then
                log_success "iCloud directory removed (was empty)"
            else
                log_info "iCloud directory not removed (contains other files)"
            fi
        fi
    fi
}

# Show remaining files
show_remaining_files() {
    log_info "Checking for remaining files..."
    
    CONFIG_DIR="$HOME/.config/claude-monitor"
    ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/claude-monitor"
    
    REMAINING_FILES=()
    
    # Check config directory
    if [[ -d "$CONFIG_DIR" ]]; then
        while IFS= read -r -d '' file; do
            REMAINING_FILES+=("$file")
        done < <(find "$CONFIG_DIR" -type f -print0 2>/dev/null || true)
    fi
    
    # Check iCloud directory
    if [[ -d "$ICLOUD_DIR" ]]; then
        while IFS= read -r -d '' file; do
            REMAINING_FILES+=("$file")
        done < <(find "$ICLOUD_DIR" -type f -print0 2>/dev/null || true)
    fi
    
    if [[ ${#REMAINING_FILES[@]} -eq 0 ]]; then
        log_success "No daemon files remaining"
    else
        log_info "Remaining files:"
        for file in "${REMAINING_FILES[@]}"; do
            echo "  • $file"
        done
        echo
        log_info "These files can be safely removed manually if desired"
    fi
}

# Verify uninstallation
verify_uninstallation() {
    log_info "Verifying uninstallation..."
    
    # Check daemon status
    if launchctl list | grep -q "$DAEMON_NAME"; then
        log_error "❌ Daemon is still loaded in launchctl"
        return 1
    else
        log_success "✅ Daemon service removed"
    fi
    
    # Check plist
    if [[ -f "$HOME/Library/LaunchAgents/$DAEMON_NAME.plist" ]]; then
        log_error "❌ Daemon plist still exists"
        return 1
    else
        log_success "✅ Daemon plist removed"
    fi
    
    # Check if client can still connect to daemon
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    if [[ -f "$PROJECT_DIR/claude_client_standalone.py" ]]; then
        cd "$PROJECT_DIR"
        # Quick test to see if client detects daemon as offline
        # This should show "daemon offline" message
        timeout 3 python3 claude_client_standalone.py 2>/dev/null || {
            if [[ $? -eq 124 ]]; then
                log_success "✅ Client correctly detects daemon as offline"
            fi
        }
    fi
    
    log_success "Uninstallation verification completed"
}

# Show completion message
show_completion() {
    log_success "🎉 Claude Monitor Daemon uninstallation completed!"
    echo
    echo "=== Uninstallation Summary ==="
    echo "• Daemon service: $DAEMON_NAME - REMOVED"
    echo "• Daemon plist: ~/Library/LaunchAgents/$DAEMON_NAME.plist - REMOVED"
    
    case $CLEANUP_OPTION in
        1)
            echo "• Data files: PRESERVED"
            ;;
        2)
            echo "• Log files: REMOVED"
            echo "• Data files: PRESERVED"
            ;;
        3)
            echo "• Log files: REMOVED"
            echo "• Monitoring data: REMOVED"
            echo "• Configuration: PRESERVED"
            ;;
        4)
            echo "• All daemon files: REMOVED"
            ;;
    esac
    
    echo
    echo "=== Next Steps ==="
    echo "• The daemon is no longer running and will not start automatically"
    echo "• You can still use the standalone monitor: python3 claude_monitor.py"
    echo "• To reinstall the daemon: run scripts/install_daemon.sh"
    
    if [[ "$REMOVE_CONFIG" != "true" ]]; then
        echo "• Your configuration and data files have been preserved"
    fi
    
    echo
}

# Main uninstallation function
main() {
    echo "=== $SCRIPT_NAME v$SCRIPT_VERSION ==="
    echo
    
    # Checks
    check_macos
    check_not_root
    check_daemon_status
    
    # If nothing is installed, exit early
    if [[ "$DAEMON_RUNNING" == "false" && "$DAEMON_INSTALLED" == "false" ]]; then
        log_info "Claude Monitor Daemon does not appear to be installed."
        log_info "Nothing to uninstall."
        exit 0
    fi
    
    # Show what will be removed
    echo "=== Uninstallation Plan ==="
    if [[ "$DAEMON_RUNNING" == "true" ]]; then
        echo "• Stop running daemon service"
    fi
    if [[ "$DAEMON_INSTALLED" == "true" ]]; then
        echo "• Remove daemon plist from LaunchAgents"
    fi
    echo "• Option to remove data files (user choice)"
    echo
    
    # Confirm uninstallation
    read -p "Proceed with uninstallation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uninstallation cancelled."
        exit 0
    fi
    
    # Get data cleanup preference
    get_cleanup_preference
    
    # Final confirmation for destructive operations
    if [[ "$REMOVE_DATA" == "true" || "$REMOVE_CONFIG" == "true" ]]; then
        echo
        log_warning "WARNING: This will permanently delete data files!"
        read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Uninstallation cancelled."
            exit 0
        fi
    fi
    
    # Uninstallation steps
    stop_daemon
    remove_plist
    cleanup_data
    verify_uninstallation
    show_remaining_files
    show_completion
    
    log_success "Uninstallation completed successfully!"
}

# Error handling
trap 'log_error "Uninstallation failed. Check the output above for details."' ERR

# Run main function
main "$@"