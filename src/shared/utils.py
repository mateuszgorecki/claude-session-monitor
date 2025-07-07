#!/usr/bin/env python3
"""
Utility functions shared across Claude session monitor components.
Common functions for time handling, formatting, validation, and system operations.
"""
import os
import sys
import subprocess
import shutil
import random
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo

from .constants import (
    Colors, UTC_TIMEZONE, PROGRESS_BAR_WIDTH, 
    PROGRESS_BAR_FILLED_CHAR, PROGRESS_BAR_EMPTY_CHAR,
    MACOS_TERMINAL_NOTIFIER_CMD, MACOS_OSASCRIPT_CMD,
    TIMING_SUGGESTIONS_POSITIVE, TIMING_SUGGESTIONS_MODERATE,
    TIMING_SUGGESTIONS_SKEPTICAL, TIMING_SUGGESTIONS_CRITICAL
)


def get_subscription_period_start(start_day: int, reference_date: Optional[date] = None) -> date:
    """
    Calculate the start date of the current subscription period.
    
    Args:
        start_day: Day of month when billing period starts (1-31)
        reference_date: Reference date (defaults to today)
        
    Returns:
        Start date of current billing period
    """
    if reference_date is None:
        reference_date = date.today()
    
    if reference_date.day >= start_day:
        return reference_date.replace(day=start_day)
    else:
        # Go to previous month
        first_day_of_current_month = reference_date.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
        return last_day_of_previous_month.replace(day=min(start_day, last_day_of_previous_month.day))


def get_next_renewal_date(start_day: int, reference_date: Optional[date] = None) -> date:
    """
    Calculate the next subscription renewal date.
    
    Args:
        start_day: Day of month when billing period starts (1-31)
        reference_date: Reference date (defaults to today)
        
    Returns:
        Next renewal date
    """
    if reference_date is None:
        reference_date = date.today()
    
    if reference_date.day >= start_day:
        # Next renewal is next month
        next_month = reference_date.month + 1
        next_year = reference_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
    else:
        # Next renewal is this month
        next_month = reference_date.month
        next_year = reference_date.year
    
    return date(next_year, next_month, start_day)


def create_progress_bar(percentage: float, width: int = PROGRESS_BAR_WIDTH) -> str:
    """
    Create a text-based progress bar.
    
    Args:
        percentage: Progress percentage (0-100)
        width: Width of progress bar in characters
        
    Returns:
        Formatted progress bar string
    """
    percentage = max(0, min(100, percentage))  # Clamp to 0-100
    filled_width = int(width * percentage / 100)
    bar = PROGRESS_BAR_FILLED_CHAR * filled_width + PROGRESS_BAR_EMPTY_CHAR * (width - filled_width)
    return f"[{bar}]"


def format_timedelta(td: timedelta) -> str:
    """
    Format timedelta as human-readable string.
    
    Args:
        td: Time delta to format
        
    Returns:
        Formatted string like "2h 30m"
    """
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 0:
        return "0h 00m"
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    return f"{hours}h {minutes:02d}m"


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if currency.upper() == "USD":
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def format_token_count(tokens: int) -> str:
    """
    Format token count with thousands separators.
    
    Args:
        tokens: Number of tokens
        
    Returns:
        Formatted token count string
    """
    return f"{tokens:,}"


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate timezone string.
    
    Args:
        timezone_str: Timezone string to validate
        
    Returns:
        True if valid timezone, False otherwise
    """
    try:
        ZoneInfo(timezone_str)
        return True
    except Exception:
        return False


def convert_timezone(dt: datetime, target_timezone: str) -> datetime:
    """
    Convert datetime to target timezone.
    
    Args:
        dt: Datetime to convert
        target_timezone: Target timezone string
        
    Returns:
        Converted datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TIMEZONE)
    
    target_tz = ZoneInfo(target_timezone)
    return dt.astimezone(target_tz)


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"


def is_command_available(command: str) -> bool:
    """
    Check if a command is available in PATH.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command is available, False otherwise
    """
    return shutil.which(command) is not None


def send_macos_notification(title: str, message: str, sound: str = "default") -> bool:
    """
    Send macOS notification using terminal-notifier or osascript.
    
    Args:
        title: Notification title
        message: Notification message
        sound: Notification sound
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    if not is_macos():
        return False
    
    # Try terminal-notifier first
    if is_command_available(MACOS_TERMINAL_NOTIFIER_CMD):
        try:
            cmd = [
                MACOS_TERMINAL_NOTIFIER_CMD,
                "-title", title,
                "-message", message,
                "-sound", sound
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            pass
    
    # Fallback to osascript
    if is_command_available(MACOS_OSASCRIPT_CMD):
        try:
            script = f'display notification "{message}" with title "{title}" sound name "{sound}"'
            subprocess.run([MACOS_OSASCRIPT_CMD, "-e", script], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            pass
    
    return False


def run_ccusage_command(since_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Run ccusage command and return parsed results.
    
    Args:
        since_date: Optional date string for filtering (YYYYMMDD format)
        
    Returns:
        Dictionary with ccusage results or error information
    """
    command = ["ccusage", "blocks", "-j"]
    if since_date:
        command.extend(["-s", since_date])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
        import json
        return json.loads(result.stdout)
    except FileNotFoundError:
        return {"error": "ccusage command not found", "blocks": []}
    except subprocess.CalledProcessError as e:
        return {"error": f"ccusage command failed: {e}", "blocks": []}
    except subprocess.TimeoutExpired:
        return {"error": "ccusage command timed out", "blocks": []}
    except json.JSONDecodeError:
        return {"error": "ccusage returned invalid JSON", "blocks": []}


def clear_terminal():
    """Clear terminal screen in a cross-platform way."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_terminal_size() -> tuple[int, int]:
    """
    Get terminal size.
    
    Returns:
        Tuple of (columns, rows)
    """
    try:
        return shutil.get_terminal_size()
    except OSError:
        return (80, 24)  # Default fallback


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except OSError:
        return False


def get_file_age_seconds(file_path: str) -> float:
    """
    Get age of file in seconds.
    
    Args:
        file_path: Path to file
        
    Returns:
        Age in seconds, or 0 if file doesn't exist
    """
    try:
        mtime = os.path.getmtime(file_path)
        return datetime.now().timestamp() - mtime
    except OSError:
        return 0.0


def is_file_stale(file_path: str, max_age_seconds: int) -> bool:
    """
    Check if file is stale (older than max_age_seconds).
    
    Args:
        file_path: Path to file
        max_age_seconds: Maximum age in seconds
        
    Returns:
        True if file is stale or doesn't exist, False otherwise
    """
    age = get_file_age_seconds(file_path)
    return age == 0.0 or age > max_age_seconds


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_percentage(part: float, total: float) -> float:
    """
    Calculate percentage, handling edge cases.
    
    Args:
        part: Part value
        total: Total value
        
    Returns:
        Percentage (0-100)
    """
    if total <= 0:
        return 0.0
    
    percentage = (part / total) * 100
    return max(0.0, min(100.0, percentage))  # Clamp to 0-100


def parse_date_string(date_str: str, format_str: str = "%Y-%m-%d") -> Optional[date]:
    """
    Parse date string safely.
    
    Args:
        date_str: Date string to parse
        format_str: Expected format
        
    Returns:
        Parsed date or None if parsing failed
    """
    try:
        return datetime.strptime(date_str, format_str).date()
    except ValueError:
        return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def get_work_timing_suggestion() -> str:
    """
    Get a work timing suggestion based on current minute of the hour.
    
    This function provides humorous timing suggestions based on Anthropic's 
    hour rounding behavior for billing sessions.
    
    Returns:
        Random timing suggestion string based on current minute:
        - 0-15 minutes: Positive suggestions
        - 16-30 minutes: Moderately positive suggestions  
        - 31-45 minutes: Skeptical suggestions
        - 46-59 minutes: Humorous/critical suggestions
    """
    current_minute = datetime.now().minute
    
    if current_minute <= 15:
        return random.choice(TIMING_SUGGESTIONS_POSITIVE)
    elif current_minute <= 30:
        return random.choice(TIMING_SUGGESTIONS_MODERATE)
    elif current_minute <= 45:
        return random.choice(TIMING_SUGGESTIONS_SKEPTICAL)
    else:
        return random.choice(TIMING_SUGGESTIONS_CRITICAL)