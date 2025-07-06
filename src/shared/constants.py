#!/usr/bin/env python3
"""
Constants and configuration values for Claude session monitor.
Centralized configuration that can be shared between daemon, client, and widget.
"""
from zoneinfo import ZoneInfo


# Application Information
APP_NAME = "Claude Session Monitor"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Claude Monitor Team"

# Daemon Version Information
DAEMON_VERSION = "1.0.0"

# Default Configuration Values
DEFAULT_TOTAL_MONTHLY_SESSIONS = 50
DEFAULT_REFRESH_INTERVAL_SECONDS = 1
DEFAULT_CCUSAGE_FETCH_INTERVAL_SECONDS = 10
DEFAULT_TIME_REMAINING_ALERT_MINUTES = 30
DEFAULT_INACTIVITY_ALERT_MINUTES = 10
DEFAULT_LOCAL_TIMEZONE = "Europe/Warsaw"
DEFAULT_BILLING_START_DAY = 1

# File Paths
DEFAULT_CONFIG_DIR = "~/.config/claude-monitor"
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_DATA_FILE = "monitor_data.json"
DEFAULT_LOG_FILE = "claude-monitor.log"

# iCloud Drive Paths
ICLOUD_CONTAINER_ID = "com~apple~CloudDocs"
ICLOUD_BASE_PATH = f"~/Library/Mobile Documents/{ICLOUD_CONTAINER_ID}"
ICLOUD_DATA_FILE = "monitor_data.json"
ICLOUD_CONFIG_FILE = "config.json"

# Daemon Configuration
DAEMON_PID_FILE = "claude-daemon.pid"
DAEMON_LOG_LEVEL = "INFO"
DAEMON_MAX_LOG_SIZE_MB = 10
DAEMON_BACKUP_COUNT = 5

# Client Configuration
CLIENT_MAX_RETRIES = 3
CLIENT_RETRY_DELAY_SECONDS = 1
CLIENT_CONNECTION_TIMEOUT_SECONDS = 5

# Data Validation Limits
MAX_SESSION_DURATION_HOURS = 24
MAX_TOKENS_PER_SESSION = 1000000
MAX_COST_PER_SESSION = 100.0
MIN_TOKENS_PER_SESSION = 0
MIN_COST_PER_SESSION = 0.0

# Progress Bar Configuration
PROGRESS_BAR_WIDTH = 40
PROGRESS_BAR_FILLED_CHAR = '█'
PROGRESS_BAR_EMPTY_CHAR = ' '

# Terminal Colors (ANSI escape codes)
class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Aliases for compatibility
    GREEN = OKGREEN
    YELLOW = WARNING
    RED = FAIL
    BLUE = OKBLUE
    CYAN = OKCYAN

# Time Zones
UTC_TIMEZONE = ZoneInfo("UTC")
LOCAL_TIMEZONE = ZoneInfo(DEFAULT_LOCAL_TIMEZONE)

# Notification Settings
NOTIFICATION_TITLE = "Claude Session Monitor"
NOTIFICATION_SOUND = "default"
NOTIFICATION_TIMEOUT_SECONDS = 5

# macOS Specific
MACOS_TERMINAL_NOTIFIER_CMD = "terminal-notifier"
MACOS_OSASCRIPT_CMD = "osascript"
MACOS_LAUNCHD_PLIST_NAME = "com.claude.monitor.daemon"

# Error Messages
ERROR_CCUSAGE_NOT_FOUND = "ccusage command not found. Please install Claude CLI tools."
ERROR_INVALID_CONFIG = "Invalid configuration detected. Using defaults."
ERROR_FILE_PERMISSION = "Permission denied accessing file."
ERROR_DISK_SPACE = "Insufficient disk space for operation."
ERROR_NETWORK_TIMEOUT = "Network operation timed out."

# Success Messages
SUCCESS_DAEMON_STARTED = "Claude monitor daemon started successfully."
SUCCESS_DAEMON_STOPPED = "Claude monitor daemon stopped successfully."
SUCCESS_CONFIG_SAVED = "Configuration saved successfully."
SUCCESS_DATA_SYNCED = "Data synchronized to iCloud successfully."

# Widget Configuration
WIDGET_UPDATE_INTERVAL_MINUTES = 1
WIDGET_MAX_SESSIONS_DISPLAY = 5
WIDGET_COMPACT_MODE_THRESHOLD = 3

# JSON Schema Validation
SCHEMA_VERSION = "1.0"
SCHEMA_REQUIRED_FIELDS = {
    'session_data': ['session_id', 'start_time', 'total_tokens', 'is_active'],
    'monitoring_data': ['current_sessions', 'total_sessions_this_month', 'last_update'],
    'config_data': ['total_monthly_sessions', 'refresh_interval_seconds'],
    'error_status': ['has_error', 'consecutive_failures']
}

# Development and Debug
DEBUG_MODE = False
VERBOSE_LOGGING = False
ENABLE_PERFORMANCE_METRICS = False