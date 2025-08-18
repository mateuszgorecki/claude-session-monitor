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
    TIMING_SUGGESTIONS_SKEPTICAL, TIMING_SUGGESTIONS_CRITICAL,
    DEFAULT_CONFIG_DIR, DEFAULT_PROJECT_CACHE_FILE,
    WINDOW_DURATION_HOURS, SUBSCRIPTION_PLANS
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


def get_project_cache_file_path() -> str:
    """
    Get the default project cache file path.
    
    Returns:
        Absolute path to the project cache file
    """
    config_dir = os.path.expanduser(DEFAULT_CONFIG_DIR)
    return os.path.join(config_dir, DEFAULT_PROJECT_CACHE_FILE)


def detect_subscription_limits() -> Dict[str, Any]:
    """
    Automatically detect subscription limits by analyzing ccusage output.
    
    This function analyzes recent ccusage data to determine the subscription type
    and automatically configure appropriate session limits.
    
    Returns:
        Dictionary with detected limits:
        {
            'total_monthly_sessions': int,
            'subscription_type': str,
            'detection_method': str,
            'confidence': str
        }
    """
    try:
        # Get recent data (last 60 days) to analyze patterns
        ccusage_data = run_ccusage_command()
        
        if "error" in ccusage_data or not ccusage_data.get("blocks"):
            return {
                'total_monthly_sessions': 50,  # Default fallback
                'subscription_type': 'unknown',
                'detection_method': 'default_fallback',
                'confidence': 'low'
            }
        
        blocks = ccusage_data["blocks"]
        
        # Analyze session patterns
        session_durations = []
        max_tokens_seen = 0
        cost_patterns = []
        
        for block in blocks:
            # Analyze session duration patterns
            if "startedAt" in block and "endedAt" in block:
                try:
                    start_time = datetime.fromisoformat(block["startedAt"].replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(block["endedAt"].replace('Z', '+00:00'))
                    duration_hours = (end_time - start_time).total_seconds() / 3600
                    session_durations.append(duration_hours)
                except (ValueError, TypeError):
                    continue
            
            # Analyze token patterns
            token_counts = block.get("tokenCounts", {})
            total_tokens = token_counts.get("inputTokens", 0) + token_counts.get("outputTokens", 0)
            max_tokens_seen = max(max_tokens_seen, total_tokens)
            
            # Analyze cost patterns
            if "costUSD" in block and block["costUSD"] > 0:
                cost_patterns.append(block["costUSD"])
        
        # Detection logic based on patterns
        detected_type = _analyze_subscription_patterns(session_durations, cost_patterns, max_tokens_seen)
        
        return detected_type
        
    except Exception as e:
        # Fallback to default on any error
        return {
            'total_monthly_sessions': 50,
            'subscription_type': 'unknown',
            'detection_method': f'error_fallback: {str(e)}',
            'confidence': 'low'
        }


def _analyze_subscription_patterns(session_durations: List[float], 
                                  cost_patterns: List[float], 
                                  max_tokens: int) -> Dict[str, Any]:
    """
    Analyze patterns to detect subscription type.
    
    Args:
        session_durations: List of session durations in hours
        cost_patterns: List of session costs
        max_tokens: Maximum tokens seen in a session
        
    Returns:
        Detection result dictionary
    """
    # Count sessions approaching 5-hour limit (Claude Max pattern)
    long_sessions = [d for d in session_durations if d > 4.5]  # Close to 5-hour limit
    
    # Check for zero-cost sessions (indicates subscription, not pay-per-use)
    zero_cost_sessions = len([c for c in cost_patterns if c == 0])
    paid_sessions = len([c for c in cost_patterns if c > 0])
    
    # Detection logic
    if zero_cost_sessions > paid_sessions:
        # Subscription model detected
        if len(long_sessions) > 2:  # Multiple long sessions indicate 5-hour limit
            return {
                'total_monthly_sessions': 50,
                'subscription_type': 'claude_max',
                'detection_method': 'pattern_analysis_long_sessions',
                'confidence': 'high'
            }
        else:
            # Could be Pro or different limit structure
            # Analyze monthly session count if we have enough data
            if len(session_durations) >= 10:  # Enough data to estimate
                # Rough estimate based on usage patterns
                if len(session_durations) > 30:  # High usage suggests higher limit
                    return {
                        'total_monthly_sessions': 100,
                        'subscription_type': 'claude_pro_enterprise',
                        'detection_method': 'pattern_analysis_high_usage',
                        'confidence': 'medium'
                    }
                else:
                    return {
                        'total_monthly_sessions': 50,
                        'subscription_type': 'claude_max',
                        'detection_method': 'pattern_analysis_moderate_usage',
                        'confidence': 'medium'
                    }
            else:
                # Insufficient data, use conservative default
                return {
                    'total_monthly_sessions': 50,
                    'subscription_type': 'claude_max_assumed',
                    'detection_method': 'pattern_analysis_insufficient_data',
                    'confidence': 'low'
                }
    else:
        # Pay-per-use detected
        return {
            'total_monthly_sessions': 1000,  # High limit for pay-per-use
            'subscription_type': 'pay_per_use',
            'detection_method': 'pattern_analysis_cost_structure',
            'confidence': 'high'
        }


def calculate_total_windows_in_period(period_start: datetime, period_end: datetime) -> int:
    """
    Calculate total number of 5-hour windows in a billing period.
    
    Args:
        period_start: Start of billing period
        period_end: End of billing period
        
    Returns:
        Total number of 5-hour windows in the period
    """
    total_duration = period_end - period_start
    total_hours = total_duration.total_seconds() / 3600
    return int(total_hours / WINDOW_DURATION_HOURS)


def calculate_remaining_windows(period_start: datetime, period_end: datetime, 
                              current_time: Optional[datetime] = None) -> int:
    """
    Calculate remaining 5-hour windows until end of billing period.
    
    Args:
        period_start: Start of billing period
        period_end: End of billing period
        current_time: Current time (defaults to now)
        
    Returns:
        Number of remaining 5-hour windows
    """
    if current_time is None:
        current_time = datetime.now(UTC_TIMEZONE)
    
    time_remaining = period_end - current_time
    if time_remaining.total_seconds() <= 0:
        return 0
    
    hours_remaining = time_remaining.total_seconds() / 3600
    return max(0, int(hours_remaining / WINDOW_DURATION_HOURS))


def detect_subscription_plan_from_ccusage(ccusage_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect subscription plan (Pro/Max 5x/Max 20x) based on ccusage data patterns.
    
    Args:
        ccusage_data: Raw ccusage command output
        
    Returns:
        Dictionary with detected plan information:
        {
            'plan_name': str,
            'prompts_per_window': int,
            'detection_method': str,
            'confidence': str
        }
    """
    if "error" in ccusage_data or not ccusage_data.get("blocks"):
        return {
            'plan_name': 'Pro',
            'prompts_per_window': SUBSCRIPTION_PLANS['Pro']['default_prompts_per_window'],
            'detection_method': 'default_fallback',
            'confidence': 'low'
        }
    
    blocks = ccusage_data["blocks"]
    
    # Analyze cost patterns to detect plan
    costs = []
    session_counts = len(blocks)
    
    for block in blocks:
        if "costUSD" in block:
            costs.append(block["costUSD"])
    
    # Detection logic based on cost structure and session patterns
    if len(costs) > 0:
        avg_cost = sum(costs) / len(costs) if costs else 0
        max_cost = max(costs) if costs else 0
        
        # High session count with low costs = higher tier subscription
        if session_counts > 100 and avg_cost < 1.0:
            return {
                'plan_name': 'Max_20x',
                'prompts_per_window': SUBSCRIPTION_PLANS['Max_20x']['default_prompts_per_window'],
                'detection_method': 'high_volume_low_cost',
                'confidence': 'high'
            }
        elif session_counts > 50 and avg_cost < 2.0:
            return {
                'plan_name': 'Max_5x',
                'prompts_per_window': SUBSCRIPTION_PLANS['Max_5x']['default_prompts_per_window'],
                'detection_method': 'medium_volume_moderate_cost',
                'confidence': 'medium'
            }
        elif max_cost > 10.0:  # High individual costs suggest pay-per-use or lower tier
            return {
                'plan_name': 'Pro',
                'prompts_per_window': SUBSCRIPTION_PLANS['Pro']['default_prompts_per_window'],
                'detection_method': 'high_individual_costs',
                'confidence': 'medium'
            }
    
    # Fallback to Pro plan
    return {
        'plan_name': 'Pro',
        'prompts_per_window': SUBSCRIPTION_PLANS['Pro']['default_prompts_per_window'],
        'detection_method': 'pattern_analysis_fallback',
        'confidence': 'low'
    }


def calculate_current_window_usage(current_time: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Calculate usage within current 5-hour window.
    
    Args:
        current_time: Current time (defaults to now)
        
    Returns:
        Dictionary with current window information:
        {
            'window_start': datetime,
            'window_end': datetime,
            'hours_into_window': float,
            'progress_percentage': float
        }
    """
    if current_time is None:
        current_time = datetime.now(UTC_TIMEZONE)
    
    # Calculate which 5-hour window we're in
    hours_since_midnight = current_time.hour + current_time.minute / 60.0
    window_index = int(hours_since_midnight / WINDOW_DURATION_HOURS)
    
    # Calculate window boundaries
    window_start_hour = window_index * WINDOW_DURATION_HOURS
    window_start = current_time.replace(hour=int(window_start_hour), 
                                       minute=int((window_start_hour % 1) * 60), 
                                       second=0, microsecond=0)
    window_end = window_start + timedelta(hours=WINDOW_DURATION_HOURS)
    
    # Calculate progress within window
    time_into_window = current_time - window_start
    hours_into_window = time_into_window.total_seconds() / 3600
    progress_percentage = (hours_into_window / WINDOW_DURATION_HOURS) * 100
    
    return {
        'window_start': window_start,
        'window_end': window_end,
        'hours_into_window': hours_into_window,
        'progress_percentage': min(100.0, progress_percentage)
    }