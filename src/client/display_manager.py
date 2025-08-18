#!/usr/bin/env python3

import sys
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

try:
    from ..shared.data_models import MonitoringData, SessionData, ActivitySessionData
except ImportError:
    from shared.data_models import MonitoringData, SessionData, ActivitySessionData


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class DisplayManager:
    """
    Manages terminal display output for the Claude monitor client.
    
    Provides the same UI/layout as the original claude_monitor.py
    with progress bars, colors, and formatting.
    """

    def __init__(self, total_monthly_sessions: int = 50):
        """
        Initialize DisplayManager.
        
        Args:
            total_monthly_sessions: Expected monthly session limit for calculations
        """
        self.total_monthly_sessions = total_monthly_sessions
        self._screen_cleared = False
        self._previous_activity_sessions = {}  # Track previous session states for change detection
        self._previous_session_state = None  # Track previous session state (active/waiting)
        self._previous_activity_session_statuses = {}  # Track activity session statuses for audio signals
        self._waiting_for_user_timestamps = {}  # Track when sessions entered WAITING_FOR_USER state
        self._long_active_timestamps = {}  # Track when sessions entered ACTIVE state
        self._long_active_alerted = set()  # Track which sessions already got long active alert
        self._timing_suggestion_cache = {}  # Cache for stable timing suggestions
        
        # Activity session display configuration
        self.activity_config = {
            "enabled": True,
            "show_inactive_sessions": True,
            "max_sessions_displayed": 10,
            "status_icons": {
                "ACTIVE": "🔵",
                "WAITING_FOR_USER": "⏳",
                "IDLE": "💤", 
                "INACTIVE": "⛔",
                "STOPPED": "⛔"
            },
            "status_colors": {
                "ACTIVE": Colors.GREEN,
                "WAITING_FOR_USER": Colors.WARNING,
                "IDLE": Colors.CYAN,
                "INACTIVE": Colors.FAIL,
                "STOPPED": Colors.FAIL
            },
            "max_project_name_length": 50,
            "show_timestamps": True,
            "verbosity": "normal"  # "minimal", "normal", "verbose"
        }

    def get_stable_timing_suggestion(self, current_time: datetime) -> tuple[str, str, str]:
        """
        Get a stable timing suggestion that doesn't change every refresh.
        
        Args:
            current_time: Current datetime
            
        Returns:
            Tuple of (icon, message, color) for stable display
        """
        # Use current hour+minute as cache key to ensure stability within the same minute
        cache_key = (current_time.hour, current_time.minute)
        
        if cache_key in self._timing_suggestion_cache:
            return self._timing_suggestion_cache[cache_key]
        
        current_minute = current_time.minute
        
        # Define timing categories with icons and messages
        if current_minute <= 15:
            # Green - optimal timing
            icon = "🟢"
            message = "Idealny czas na rozpoczęcie pracy!"
            color = Colors.GREEN
        elif current_minute <= 30:
            # Yellow - moderate timing
            icon = "🟡"
            message = "Można zaczynać, timing akceptowalny"
            color = Colors.WARNING
        elif current_minute <= 45:
            # Orange - skeptical timing
            icon = "🟠"
            message = "Timing mógłby być lepszy, ale OK"
            color = Colors.WARNING
        else:
            # Red - critical timing
            icon = "🔴"
            message = "Najgorszy możliwy moment na start"
            color = Colors.FAIL
        
        # Cache the result
        result = (icon, message, color)
        self._timing_suggestion_cache[cache_key] = result
        
        # Clean old cache entries (keep only last 5 entries)
        if len(self._timing_suggestion_cache) > 5:
            # Remove oldest entries
            sorted_keys = sorted(self._timing_suggestion_cache.keys())
            for old_key in sorted_keys[:-5]:
                del self._timing_suggestion_cache[old_key]
        
        return result

    def play_audio_signal(self):
        """Play a short audio signal using system beep - two quick beeps."""
        try:
            # Use osascript for better SSH compatibility (plays on host)
            subprocess.run(['osascript', '-e', 'beep 2'], 
                          check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            # Fallback to afplay for local sessions - play twice quickly
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], 
                              check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], 
                              check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                # Final fallback to terminal bell - two quick beeps
                try:
                    print('\a\a', end='', flush=True)
                except Exception:
                    pass  # Ignore if audio signal fails

    def play_long_active_alert(self):
        """Play a longer alert signal for long ACTIVE sessions - three quick beeps."""
        try:
            # Use osascript for better SSH compatibility (plays on host)
            subprocess.run(['osascript', '-e', 'beep 3'], 
                          check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # Fallback to afplay for local sessions - play three times quickly
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], 
                              check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], 
                              check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], 
                              check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                # Final fallback to terminal bell - three quick beeps
                try:
                    print('\a\a\a', end='', flush=True)
                except Exception:
                    pass  # Ignore if audio signal fails

    def create_progress_bar(self, percentage: float, width: int = 40) -> str:
        """
        Create a progress bar string identical to claude_monitor.py.
        
        Args:
            percentage: Progress percentage (0-100)
            width: Width of progress bar in characters
            
        Returns:
            Formatted progress bar string
        """
        filled_width = int(width * percentage / 100)
        bar = '█' * filled_width + ' ' * (width - filled_width)
        return f"[{bar}]"

    def format_timedelta(self, td: timedelta) -> str:
        """
        Format timedelta as "Xh YYm" identical to claude_monitor.py.
        
        Args:
            td: Time delta to format
            
        Returns:
            Formatted time string
        """
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours}h {minutes:02d}m"

    def clear_screen(self):
        """Clear screen and hide cursor like claude_monitor.py."""
        print("\033[H\033[J\033[?25l", end="")
    
    def move_to_top(self):
        """Move cursor to top without clearing screen - prevents flicker."""
        print("\033[H", end="")

    def calculate_token_usage_percentage(self, current_tokens: int, max_tokens: int) -> float:
        """
        Calculate token usage percentage.
        
        Args:
            current_tokens: Current token count
            max_tokens: Maximum token limit
            
        Returns:
            Percentage as float
        """
        if max_tokens <= 0:
            return 0.0
        return (current_tokens / max_tokens) * 100

    def calculate_time_progress_percentage(self, start_time: datetime, end_time: datetime, 
                                         current_time: datetime) -> float:
        """
        Calculate time progress percentage through session.
        
        Args:
            start_time: Session start time
            end_time: Session end time  
            current_time: Current time
            
        Returns:
            Progress percentage as float
        """
        time_remaining = end_time - current_time
        time_total = end_time - start_time
        
        if time_total.total_seconds() <= 0:
            return 100.0
            
        progress = (1 - (time_remaining.total_seconds() / time_total.total_seconds())) * 100
        return max(0.0, min(100.0, progress))

    def find_active_session(self, monitoring_data: MonitoringData) -> Optional[SessionData]:
        """
        Find the currently active session from monitoring data.
        
        Args:
            monitoring_data: Current monitoring data
            
        Returns:
            Active session if found, None otherwise
        """
        for session in monitoring_data.current_sessions:
            if session.is_active:
                return session
        return None

    def calculate_window_stats(self, monitoring_data) -> Dict[str, Any]:
        """
        Calculate 5-hour window usage statistics.
        
        Args:
            monitoring_data: Current monitoring data
            
        Returns:
            Dictionary with window statistics including plan detection
        """
        try:
            try:
                from ..shared.utils import (
                    calculate_total_windows_in_period,
                    calculate_remaining_windows,
                    detect_subscription_plan_from_ccusage,
                    run_ccusage_command,
                    calculate_current_window_usage
                )
            except ImportError:
                from shared.utils import (
                    calculate_total_windows_in_period,
                    calculate_remaining_windows,
                    detect_subscription_plan_from_ccusage,
                    run_ccusage_command,
                    calculate_current_window_usage
                )
            
            # Calculate total windows in billing period
            total_windows = calculate_total_windows_in_period(
                monitoring_data.billing_period_start,
                monitoring_data.billing_period_end
            )
            
            # Calculate remaining windows
            remaining_windows = calculate_remaining_windows(
                monitoring_data.billing_period_start,
                monitoring_data.billing_period_end
            )
            
            # Detect subscription plan
            ccusage_data = run_ccusage_command()
            plan_info = detect_subscription_plan_from_ccusage(ccusage_data)
            
            # Calculate current window usage
            current_window = calculate_current_window_usage()
            
            # Calculate current window prompts from sessions within the current window
            current_window_prompts = 0
            window_start = current_window['window_start']
            window_end = current_window['window_end']
            
            # Count sessions that started within the current 5-hour window
            for session in monitoring_data.current_sessions:
                if window_start <= session.start_time <= window_end:
                    current_window_prompts += 1
            
            max_prompts_per_window = plan_info['prompts_per_window']
            
            return {
                'total_windows': total_windows,
                'remaining_windows': remaining_windows,
                'windows_used': total_windows - remaining_windows,
                'plan_name': plan_info['plan_name'],
                'current_window_prompts': current_window_prompts,
                'max_prompts_per_window': max_prompts_per_window,
                'current_window_start': current_window['window_start'],
                'current_window_end': current_window['window_end'],
                'plan_confidence': plan_info['confidence']
            }
        except ImportError:
            # Fallback to old session-based calculation
            return self.calculate_session_stats_fallback(monitoring_data)
        except Exception:
            # Fallback to old session-based calculation for any other error
            return self.calculate_session_stats_fallback(monitoring_data)
    
    def calculate_session_stats_fallback(self, monitoring_data) -> Dict[str, Any]:
        """
        Fallback to session-based calculation if new system fails.
        
        Args:
            monitoring_data: Current monitoring data
            
        Returns:
            Dictionary with session statistics (legacy)
        """
        total_monthly_sessions = self.total_monthly_sessions
        current_sessions = monitoring_data.total_sessions_this_month
        
        period_duration = monitoring_data.billing_period_end - monitoring_data.billing_period_start
        days_in_period = period_duration.days
        days_remaining = (monitoring_data.billing_period_end.date() - datetime.now(timezone.utc).date()).days
        
        sessions_used = current_sessions
        sessions_left = total_monthly_sessions - current_sessions
        
        # Calculate average sessions per day for remaining period
        if days_remaining > 0:
            avg_sessions_per_day = sessions_left / days_remaining
        else:
            avg_sessions_per_day = float(sessions_left)  # If last day
            
        return {
            'sessions_used': sessions_used,
            'sessions_left': sessions_left,
            'avg_sessions_per_day': avg_sessions_per_day,
            'is_fallback': True
        }

    def render_active_session_display(self, monitoring_data: MonitoringData, 
                                    active_session: SessionData):
        """
        Render display for when there's an active session.
        
        Args:
            monitoring_data: Current monitoring data
            active_session: The active session to display
        """
        # Calculate window statistics
        window_stats = self.calculate_window_stats(monitoring_data)
        
        if not window_stats.get('is_fallback'):
            # Display 5-hour window information
            remaining_windows = window_stats['remaining_windows']
            total_windows = window_stats['total_windows']
            
            # Calculate percentage for progress bar
            window_percentage = ((total_windows - remaining_windows) / total_windows * 100) if total_windows > 0 else 0
            progress_bar = self.create_progress_bar(window_percentage)
            
            print(f"⏰ 5h Windows: {Colors.GREEN}{progress_bar}{Colors.ENDC} {remaining_windows}/{total_windows} remaining")
            
            # Current window information
            current_prompts = window_stats['current_window_prompts']
            max_prompts = window_stats['max_prompts_per_window']
            plan_name = window_stats['plan_name'].replace('_', ' ')
            
            print(f"🔥 Current window: {current_prompts}/{max_prompts} prompts used ({plan_name} Plan)")
            
            # Show subscription period start
            period_start = monitoring_data.billing_period_start.strftime('%Y-%m-%d')
            days_remaining = (monitoring_data.billing_period_end.date() - datetime.now(timezone.utc).date()).days
            print(f"📅 Started: {period_start} ({days_remaining} days remaining)")
        else:
            # Fallback to original token/time display
            # Calculate token usage percentage
            token_usage_percent = self.calculate_token_usage_percentage(
                active_session.total_tokens, monitoring_data.max_tokens_per_session
            )
            
            # Calculate time progress
            current_time = datetime.now(timezone.utc)
            time_progress_percent = self.calculate_time_progress_percentage(
                active_session.start_time, active_session.end_time, current_time
            )
            
            # Calculate time remaining
            time_remaining = active_session.end_time - current_time
            
            # Display progress bars (same format as claude_monitor.py)
            print(f"Token Usage:   {Colors.GREEN}{self.create_progress_bar(token_usage_percent)}{Colors.ENDC} {token_usage_percent:.1f}%")
            print(f"Time to Reset: {Colors.BLUE}{self.create_progress_bar(time_progress_percent)}{Colors.ENDC} {self.format_timedelta(time_remaining)}")
            
            # Display session details
            print(f"\n{Colors.BOLD}Tokens:{Colors.ENDC}        {active_session.total_tokens:,} / ~{monitoring_data.max_tokens_per_session:,}")
            print(f"{Colors.BOLD}Session Cost:{Colors.ENDC}  ${active_session.cost_usd:.2f}\n")

    def render_waiting_display(self, monitoring_data: MonitoringData):
        """
        Render display when waiting for a new session to start.
        
        Args:
            monitoring_data: Current monitoring data
        """
        # Calculate window statistics
        window_stats = self.calculate_window_stats(monitoring_data)
        
        if not window_stats.get('is_fallback'):
            # Display 5-hour window information
            remaining_windows = window_stats['remaining_windows']
            total_windows = window_stats['total_windows']
            
            # Calculate percentage for progress bar
            window_percentage = ((total_windows - remaining_windows) / total_windows * 100) if total_windows > 0 else 0
            progress_bar = self.create_progress_bar(window_percentage)
            
            print(f"⏰ 5h Windows: {Colors.GREEN}{progress_bar}{Colors.ENDC} {remaining_windows}/{total_windows} remaining")
            
            # Current window information
            current_prompts = window_stats['current_window_prompts']
            max_prompts = window_stats['max_prompts_per_window']
            plan_name = window_stats['plan_name'].replace('_', ' ')
            
            print(f"🔥 Current window: {current_prompts}/{max_prompts} prompts used ({plan_name} Plan)")
            
            # Show subscription period start
            period_start = monitoring_data.billing_period_start.strftime('%Y-%m-%d')
            days_remaining = (monitoring_data.billing_period_end.date() - datetime.now(timezone.utc).date()).days
            print(f"📅 Started: {period_start} ({days_remaining} days remaining)")
        else:
            # Fallback to old display
            print(f"\n{Colors.WARNING}Waiting for a new session to start...{Colors.ENDC}\n")
            print(f"Saved max tokens: {monitoring_data.max_tokens_per_session:,}")
            
            # Show current subscription period start
            period_start = monitoring_data.billing_period_start.strftime('%Y-%m-%d')
            print(f"Current subscription period started: {period_start}")
        
        # Get stable timing suggestion with icon and colored time
        current_time = datetime.now()
        icon, message, color = self.get_stable_timing_suggestion(current_time)
        
        # Display timing suggestion with icon and colored time
        colored_time = f"{color}{current_time.strftime('%H:%M')}{Colors.ENDC}"
        print(f"\n{icon} {color}{message}{Colors.ENDC} ({colored_time})\n")

    def render_footer(self, current_time: datetime, window_stats: Dict[str, Any],
                     days_remaining: int, total_cost: float, daemon_version: Optional[str] = None):
        """
        Render footer with 5-hour window statistics and cost.
        
        Args:
            current_time: Current local time
            window_stats: Window usage statistics
            days_remaining: Days remaining in billing period
            total_cost: Total cost for the month
            daemon_version: Daemon version if available
        """
        print("=" * 60)
        
        if window_stats.get('is_fallback'):
            # Fallback to old session display
            footer_line1 = (
                f"⏰ {current_time.strftime('%H:%M:%S')}   "
                f"🗓️ Sessions: {Colors.BOLD}{window_stats['sessions_used']} used, "
                f"{window_stats['sessions_left']} left{Colors.ENDC} | "
                f"💰 Cost (mo): ${total_cost:.2f}"
            )
            
            version_info = daemon_version if daemon_version else "unknown"
            footer_line2 = (
                f"  └─ ⏳ {days_remaining}d left "
                f"(avg {window_stats['avg_sessions_per_day']:.1f}/day) | "
                f"🖥️ Server: {version_info} | Ctrl+C exit"
            )
        else:
            # New 5-hour window display
            remaining_windows = window_stats['remaining_windows']
            total_windows = window_stats['total_windows']
            
            footer_line1 = (
                f"⏰ {current_time.strftime('%H:%M:%S')}   "
                f"💰 Cost (mo): ${total_cost:.2f}"
            )
            
            version_info = daemon_version if daemon_version else "unknown"
            footer_line2 = (
                f"  └─ ⏳ {days_remaining}d left | "
                f"🖥️ Server: {version_info} | Ctrl+C exit"
            )
        
        print(footer_line1)
        print(footer_line2)

    def _render_activity_sessions(self, activity_sessions: List[ActivitySessionData]):
        """
        Render Claude Code activity sessions with configurable display options.
        
        Args:
            activity_sessions: List of activity sessions to display
        """
        # Check if activity sessions display is enabled
        if not self.activity_config["enabled"]:
            return
        
        if not activity_sessions:
            print(f"\n{Colors.CYAN}No activity sessions found{Colors.ENDC}")
            return
        
        # Filter sessions based on configuration
        filtered_sessions = self._filter_activity_sessions(activity_sessions)
        
        if not filtered_sessions:
            if self.activity_config["verbosity"] != "minimal":
                print(f"\n{Colors.CYAN}No activity sessions to display{Colors.ENDC}")
            return
        
        # Calculate dynamic alignment based on longest project name
        max_length = self.activity_config["max_project_name_length"]
        longest_display_name = 0
        for session in filtered_sessions:
            display_name = session.project_name[:max_length] + "..." if len(session.project_name) > max_length else session.project_name
            longest_display_name = max(longest_display_name, len(display_name))
        
        # Add one space for separator before dash
        longest_display_name += 1
        
        # Activity sessions header
        verbosity = self.activity_config["verbosity"]
        if verbosity == "minimal":
            print(f"\n{Colors.HEADER}Activity: {len(filtered_sessions)} sessions{Colors.ENDC}")
        else:
            print(f"\n{Colors.HEADER}{Colors.BOLD}CLAUDE CODE ACTIVITY{Colors.ENDC}")
            print(f"{Colors.HEADER}{'=' * 20}{Colors.ENDC}")
        
        # Display sessions based on verbosity
        for session in filtered_sessions:
            self._render_single_activity_session(session, verbosity, longest_display_name)
        
        if verbosity != "minimal":
            print()  # Empty line after activity sessions

    def _filter_activity_sessions(self, sessions: List[ActivitySessionData]) -> List[ActivitySessionData]:
        """
        Filter activity sessions based on configuration.
        
        Args:
            sessions: List of all activity sessions
            
        Returns:
            Filtered list of sessions
        """
        filtered = sessions
        
        # Filter out inactive sessions if configured
        if not self.activity_config["show_inactive_sessions"]:
            filtered = [s for s in filtered if s.status != "INACTIVE"]
        
        # Sort by start time (most recent first) and limit
        filtered = sorted(filtered, key=lambda s: s.start_time, reverse=True)
        max_sessions = self.activity_config["max_sessions_displayed"]
        
        return filtered[:max_sessions]

    def _check_activity_session_changes(self, activity_sessions: List[ActivitySessionData]):
        """
        Check for activity session status changes and play audio signal when WAITING_FOR_USER lasts >=30 seconds.
        
        Args:
            activity_sessions: Current list of activity sessions
        """
        from datetime import datetime, timezone
        
        
        # Track current session statuses
        current_statuses = {}
        for session in activity_sessions:
            session_key = session.project_name  # Use project_name only, not session_id
            current_statuses[session_key] = session.status
        
        current_time = datetime.now(timezone.utc)
        
        # Check for status changes and track WAITING_FOR_USER timestamps
        for session_key, current_status in current_statuses.items():
            previous_status = self._previous_activity_session_statuses.get(session_key)
            
            if current_status == "WAITING_FOR_USER":
                # Track when session enters WAITING_FOR_USER state (from any state or new session)
                if (previous_status != "WAITING_FOR_USER" and 
                    session_key not in self._waiting_for_user_timestamps):
                    self._waiting_for_user_timestamps[session_key] = current_time
            
            elif current_status != "WAITING_FOR_USER":
                # Remove timestamp if session leaves WAITING_FOR_USER state
                if session_key in self._waiting_for_user_timestamps:
                    del self._waiting_for_user_timestamps[session_key]
                # Clear audio played flag when leaving WAITING_FOR_USER
                if hasattr(self, '_audio_played_sessions') and session_key in self._audio_played_sessions:
                    self._audio_played_sessions.remove(session_key)
        
        # Check for WAITING_FOR_USER sessions that have lasted >=25 seconds
        for session in activity_sessions:
            if session.status == "WAITING_FOR_USER":
                session_key = session.project_name
                
                # Track last event time to detect new activity
                if not hasattr(self, '_last_event_times'):
                    self._last_event_times = {}
                
                current_event_time = session.metadata.get('last_event_time') if session.metadata else None
                previous_event_time = self._last_event_times.get(session_key)
                
                # Clear audio flag if there's new activity (last_event_time changed)
                if current_event_time != previous_event_time:
                    if hasattr(self, '_audio_played_sessions') and session_key in self._audio_played_sessions:
                        self._audio_played_sessions.remove(session_key)
                    self._last_event_times[session_key] = current_event_time
                
                # Use same time calculation as display (from last_event_time)
                if session.metadata and 'last_event_time' in session.metadata:
                    try:
                        reference_time = datetime.fromisoformat(session.metadata['last_event_time'])
                        wait_duration = current_time - reference_time
                        if wait_duration.total_seconds() >= 25:
                            # Prevent repeated alerts for same session
                            if session_key not in getattr(self, '_audio_played_sessions', set()):
                                self.play_audio_signal()
                                if not hasattr(self, '_audio_played_sessions'):
                                    self._audio_played_sessions = set()
                                self._audio_played_sessions.add(session_key)
                                break  # Only play once per update cycle
                    except (ValueError, KeyError):
                        continue
        
        # Clean up timestamps for sessions that no longer exist
        existing_sessions = set(current_statuses.keys())
        timestamps_to_remove = [key for key in self._waiting_for_user_timestamps.keys() 
                               if key not in existing_sessions]
        for key in timestamps_to_remove:
            del self._waiting_for_user_timestamps[key]
        
        # Update previous statuses
        self._previous_activity_session_statuses = current_statuses.copy()

    def _check_long_active_sessions(self, activity_sessions: List[ActivitySessionData]):
        """
        Check for ACTIVE sessions that have lasted >5 minutes and trigger alert.
        
        Args:
            activity_sessions: Current list of activity sessions
        """
        from datetime import datetime, timezone
        
        # Track current session statuses
        current_statuses = {}
        for session in activity_sessions:
            session_key = session.project_name  # Use project_name only, not session_id
            current_statuses[session_key] = session.status
        
        current_time = datetime.now(timezone.utc)
        
        # Check for status changes and track ACTIVE timestamps
        for session in activity_sessions:
            session_key = session.project_name
            current_status = session.status
            
            # Handle new ACTIVE sessions (not seen before)
            if session_key not in self._previous_activity_session_statuses and current_status == "ACTIVE":
                # Use actual session start time for new sessions
                self._long_active_timestamps[session_key] = session.start_time
                self._long_active_alerted.discard(session_key)
            
            # Handle existing sessions
            elif session_key in self._previous_activity_session_statuses:
                previous_status = self._previous_activity_session_statuses[session_key]
                
                # Track when session enters ACTIVE state
                if (previous_status != "ACTIVE" and current_status == "ACTIVE"):
                    # Use actual session start time when transitioning to ACTIVE
                    self._long_active_timestamps[session_key] = session.start_time
                    # Reset alert flag when session becomes active again
                    self._long_active_alerted.discard(session_key)
                
                # Remove timestamp if session leaves ACTIVE state
                elif (previous_status == "ACTIVE" and current_status != "ACTIVE"):
                    if session_key in self._long_active_timestamps:
                        del self._long_active_timestamps[session_key]
                    self._long_active_alerted.discard(session_key)
        
        # Check for ACTIVE sessions that have lasted >5 minutes
        for session in activity_sessions:
            if session.status == "ACTIVE":
                session_key = session.project_name
                
                # Track last event time to detect new activity (similar to WAITING_FOR_USER logic)
                if not hasattr(self, '_last_active_event_times'):
                    self._last_active_event_times = {}
                
                current_event_time = session.metadata.get('last_event_time') if session.metadata else None
                previous_event_time = self._last_active_event_times.get(session_key)
                
                # Clear alert flag if there's new activity (last_event_time changed)
                if current_event_time != previous_event_time:
                    self._long_active_alerted.discard(session_key)
                    self._last_active_event_times[session_key] = current_event_time
                
                # Use same time calculation as display (from last_event_time)
                if session.metadata and 'last_event_time' in session.metadata:
                    try:
                        reference_time = datetime.fromisoformat(session.metadata['last_event_time'])
                        active_duration = current_time - reference_time
                        if active_duration.total_seconds() >= 300:  # 5 minutes = 300 seconds
                            # Prevent repeated alerts for same session
                            if session_key not in self._long_active_alerted:
                                self.play_long_active_alert()
                                self._long_active_alerted.add(session_key)
                                break  # Only alert once per update cycle
                    except (ValueError, KeyError):
                        continue
        
        # Clean up timestamps for sessions that no longer exist
        existing_sessions = set(current_statuses.keys())
        timestamps_to_remove = [key for key in self._long_active_timestamps.keys() 
                               if key not in existing_sessions]
        for key in timestamps_to_remove:
            del self._long_active_timestamps[key]
        
        # Clean up alert flags for sessions that no longer exist
        self._long_active_alerted = {key for key in self._long_active_alerted 
                                    if key in existing_sessions}

    def _check_activity_session_changes_without_audio(self, activity_sessions: List[ActivitySessionData]) -> bool:
        """
        Check for activity session status changes that should trigger audio signal, but don't play it.
        
        Args:
            activity_sessions: Current list of activity sessions
            
        Returns:
            bool: True if there's a status change that should trigger audio (WAITING_FOR_USER >=30s), False otherwise
        """
        from datetime import datetime, timezone
        
        # Track current session statuses
        current_statuses = {}
        for session in activity_sessions:
            session_key = session.project_name  # Use project_name only, not session_id
            current_statuses[session_key] = session.status
        
        current_time = datetime.now(timezone.utc)
        
        # Check for status changes and track WAITING_FOR_USER timestamps
        for session_key, current_status in current_statuses.items():
            if session_key in self._previous_activity_session_statuses:
                previous_status = self._previous_activity_session_statuses[session_key]
                
                # Track when session enters WAITING_FOR_USER state
                if (previous_status == "ACTIVE" and current_status == "WAITING_FOR_USER"):
                    self._waiting_for_user_timestamps[session_key] = current_time
                
                # Remove timestamp if session leaves WAITING_FOR_USER state
                elif (previous_status == "WAITING_FOR_USER" and current_status != "WAITING_FOR_USER"):
                    if session_key in self._waiting_for_user_timestamps:
                        del self._waiting_for_user_timestamps[session_key]
        
        # Check for WAITING_FOR_USER sessions that have lasted >=30 seconds
        audio_signal_needed = False
        for session_key, current_status in current_statuses.items():
            if (current_status == "WAITING_FOR_USER" and 
                session_key in self._waiting_for_user_timestamps):
                
                wait_duration = current_time - self._waiting_for_user_timestamps[session_key]
                if wait_duration.total_seconds() >= 30:
                    audio_signal_needed = True
                    # Remove timestamp to prevent repeated audio signals
                    del self._waiting_for_user_timestamps[session_key]
                    break  # Only need to detect once per update cycle
        
        # Clean up timestamps for sessions that no longer exist
        existing_sessions = set(current_statuses.keys())
        timestamps_to_remove = [key for key in self._waiting_for_user_timestamps.keys() 
                               if key not in existing_sessions]
        for key in timestamps_to_remove:
            del self._waiting_for_user_timestamps[key]
        
        # Update previous statuses
        self._previous_activity_session_statuses = current_statuses.copy()
        
        return audio_signal_needed

    def _has_activity_sessions_changed(self, current_sessions: List[ActivitySessionData]) -> bool:
        """
        Check if activity sessions have changed (status, count, or sessions themselves).
        
        Args:
            current_sessions: Current list of activity sessions
            
        Returns:
            True if sessions have changed, False otherwise
        """
        # Create current session state map
        current_state = {}
        for session in current_sessions:
            session_key = f"{session.project_name}_{session.session_id}"
            current_state[session_key] = session.status
        
        # Check if session count changed
        if len(current_state) != len(self._previous_activity_sessions):
            self._previous_activity_sessions = current_state
            return True
        
        # Check if any session status changed or new sessions appeared
        for session_key, status in current_state.items():
            if session_key not in self._previous_activity_sessions:
                # New session appeared
                self._previous_activity_sessions = current_state
                return True
            elif self._previous_activity_sessions[session_key] != status:
                # Status changed
                self._previous_activity_sessions = current_state
                return True
        
        # Check if any sessions disappeared
        for session_key in self._previous_activity_sessions:
            if session_key not in current_state:
                # Session disappeared
                self._previous_activity_sessions = current_state
                return True
        
        # No changes detected
        return False

    def _get_activity_time_str(self, session: ActivitySessionData) -> str:
        """
        Calculate and format current action duration for all sessions.
        
        Args:
            session: Activity session to analyze
            
        Returns:
            Formatted time string (mm:ss) showing time since last activity/event
        """
        # For all sessions, use last event time from metadata if available
        # This shows duration of current action (for ACTIVE) or time since last action (for others)
        if session.metadata and 'last_event_time' in session.metadata:
            try:
                from datetime import datetime, timezone
                reference_time = datetime.fromisoformat(session.metadata['last_event_time'])
            except (ValueError, KeyError):
                # Fallback to session start time if metadata is invalid
                reference_time = session.start_time
        else:
            # Fallback to session start time if no metadata
            reference_time = session.start_time
        
        # Calculate time difference
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc)
        time_diff = current_time - reference_time
        total_seconds = int(time_diff.total_seconds())
        
        # Format as mm:ss
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"({minutes:02d}:{seconds:02d})"

    def _is_long_active_session(self, session: ActivitySessionData) -> bool:
        """
        Check if an ACTIVE session has been running for more than 5 minutes.
        
        Args:
            session: Activity session to check
            
        Returns:
            bool: True if session is ACTIVE and >5 minutes, False otherwise
        """
        if session.status != "ACTIVE":
            return False
        
        session_key = session.project_name  # Use same key as in _check_long_active_sessions
        if session_key not in self._long_active_timestamps:
            return False
        
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc)
        active_duration = current_time - self._long_active_timestamps[session_key]
        return active_duration.total_seconds() >= 300  # 5 minutes = 300 seconds

    def _render_single_activity_session(self, session: ActivitySessionData, verbosity: str, alignment_width: int = 0):
        """
        Render a single activity session based on verbosity level.
        
        Args:
            session: Activity session to render
            verbosity: Display verbosity level
            alignment_width: Width for project name alignment (dynamic)
        """
        # Get icon and color from configuration
        icon = self.activity_config["status_icons"].get(session.status, "❓")
        color = self.activity_config["status_colors"].get(session.status, Colors.ENDC)
        
        # Add red exclamation mark for long ACTIVE sessions
        if self._is_long_active_session(session):
            icon = f"{icon}❗"
            color = Colors.FAIL  # Red color for long active sessions
        
        # Format project name with truncation and alignment
        max_length = self.activity_config["max_project_name_length"]
        project_name_display = session.project_name[:max_length] + "..." if len(session.project_name) > max_length else session.project_name
        # Align to the longest project name width
        project_name_aligned = project_name_display.ljust(alignment_width)
        
        # Get activity/inactivity time for all sessions
        time_str = self._get_activity_time_str(session)
        
        if verbosity == "minimal":
            # Compact display: just icon and status
            print(f"{icon} {color}{session.status}{Colors.ENDC}", end=" ")
        elif verbosity == "normal":
            # Normal display: icon, project name, status, activity/inactivity time
            time_info = f" {time_str}" if time_str else ""
            
            print(f"{icon} {color}{Colors.BOLD}{project_name_aligned}{Colors.ENDC}- {color}{session.status}{Colors.ENDC}{time_info}")
        elif verbosity == "verbose":
            # Verbose display: all details including event type and metadata
            # Convert UTC to local time for display
            local_time = session.start_time.replace(tzinfo=timezone.utc).astimezone()
            timestamp_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
            event_info = f" [{session.event_type}]" if session.event_type else ""
            
            print(f"{icon} {color}{Colors.BOLD}{project_name_display}{Colors.ENDC}")
            status_line = f"   Status: {color}{session.status}{Colors.ENDC} | Time: {timestamp_str}{event_info}"
            if time_str and session.status != "ACTIVE":
                status_line += f" | Inactive: {time_str}"
            elif time_str and session.status == "ACTIVE":
                status_line += f" | Active: {time_str}"
            print(status_line)
            
            if session.metadata:
                metadata_str = ", ".join([f"{k}={v}" for k, v in session.metadata.items() if k != 'last_event_time'])
                if metadata_str:
                    print(f"   Metadata: {metadata_str}")
        
        # Add newline for minimal mode after all sessions
        if verbosity == "minimal":
            print()  # Single newline at the end

    def render_full_display(self, monitoring_data: MonitoringData):
        """
        Render the complete display exactly like claude_monitor.py.
        
        Args:
            monitoring_data: Current monitoring data to display
            
        Returns:
            bool: True if data refresh is needed (activity sessions changed), False otherwise
        """
        # Check if activity sessions have changed for screen clearing decision
        activity_sessions = monitoring_data.activity_sessions or []
        sessions_changed = self._has_activity_sessions_changed(activity_sessions)
        
        # Check for active session
        active_session = self.find_active_session(monitoring_data)
        
        # Determine current session state
        current_session_state = "active" if active_session else "waiting"
        
        # Check if state changed from active to waiting - will play audio after screen refresh
        session_state_changed = (self._previous_session_state == "active" and 
                                current_session_state == "waiting")
        
        # Check for main session state transitions that require screen clearing
        main_session_state_changed = (self._previous_session_state is not None and 
                                     self._previous_session_state != current_session_state)
        
        # Check for activity session status changes - will play audio after screen refresh
        activity_sessions = getattr(monitoring_data, 'activity_sessions', None) or []
        activity_status_changed = self._check_activity_session_changes_without_audio(activity_sessions)
        
        # Update previous session state
        self._previous_session_state = current_session_state
        
        # Clear screen on first run, when activity sessions change, or when main session state changes
        if not self._screen_cleared or sessions_changed or main_session_state_changed:
            self.clear_screen()
            self._screen_cleared = True
        else:
            self.move_to_top()
        
        # Header (same as claude_monitor.py)
        print(f"{Colors.HEADER}{Colors.BOLD}✦ ✧ ✦ CLAUDE SESSION MONITOR ✦ ✧ ✦{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 35}{Colors.ENDC}\n")
        
        # Get current time
        current_time = datetime.now()
        
        # Calculate billing period info
        period_duration = monitoring_data.billing_period_end - monitoring_data.billing_period_start
        days_in_period = period_duration.days
        days_remaining = (monitoring_data.billing_period_end.date() - datetime.now(timezone.utc).date()).days
        
        # Calculate window statistics (replaces session statistics)
        window_stats = self.calculate_window_stats(monitoring_data)
        
        if active_session:
            # Render active session display
            self.render_active_session_display(monitoring_data, active_session)
        else:
            # Render waiting display
            self.render_waiting_display(monitoring_data)
        
        # Render activity sessions if available
        activity_sessions = getattr(monitoring_data, 'activity_sessions', None) or []
        
        # Check for activity session changes and play audio if needed (always run, regardless of display settings)
        self._check_activity_session_changes(activity_sessions)
        
        # Check for long ACTIVE sessions and play alert if needed (always run, regardless of display settings)
        self._check_long_active_sessions(activity_sessions)
        
        self._render_activity_sessions(activity_sessions)
        
        # Render footer
        self.render_footer(current_time, window_stats, days_remaining, 
                          monitoring_data.total_cost_this_month, monitoring_data.daemon_version)
        
        # Flush output to ensure screen refresh is complete
        sys.stdout.flush()
        
        # Return whether data refresh is needed
        return sessions_changed

    def show_cursor(self):
        """Show terminal cursor."""
        print("\033[?25h", end="")

    def show_exit_message(self):
        """Show exit message when closing monitor."""
        self.show_cursor()
        print(f"\n\n{Colors.WARNING}Closing monitor...{Colors.ENDC}")

    def show_error_message(self, message: str):
        """
        Show error message in red.
        
        Args:
            message: Error message to display
        """
        print(f"{Colors.FAIL}Error: {message}{Colors.ENDC}")

    def show_warning_message(self, message: str):
        """
        Show warning message in yellow.
        
        Args:
            message: Warning message to display
        """
        print(f"{Colors.WARNING}Warning: {message}{Colors.ENDC}")

    def show_info_message(self, message: str):
        """
        Show info message in cyan.
        
        Args:
            message: Info message to display
        """
        print(f"{Colors.CYAN}{message}{Colors.ENDC}")
    
    def render_daemon_offline_display(self):
        """
        Render full-screen display when daemon is offline, matching claude_monitor.py style.
        """
        # Clear screen only on first run, then just move to top
        if not self._screen_cleared:
            self.clear_screen()
            self._screen_cleared = True
        else:
            self.move_to_top()
        
        # Header (same as normal display)
        print(f"{Colors.HEADER}{Colors.BOLD}✦ ✧ ✦ CLAUDE SESSION MONITOR ✦ ✧ ✦{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 35}{Colors.ENDC}\n")
        
        # Server status message
        print(f"\n{Colors.FAIL}⚠️  SERVER NOT RUNNING{Colors.ENDC}")
        print(f"\n{Colors.WARNING}The Claude monitor server is currently offline.{Colors.ENDC}")
        print(f"{Colors.WARNING}Please start the server to see real-time monitoring data.{Colors.ENDC}\n")
        
        # Instructions
        print(f"{Colors.CYAN}To start the server:{Colors.ENDC}")
        print(f"  python3 -m src.daemon.claude_daemon\n")
        print(f"{Colors.CYAN}Or use the original monitor:{Colors.ENDC}")
        print(f"  python3 claude_monitor.py\n")
        
        # Footer (simplified)
        current_time = datetime.now()
        print("=" * 60)
        print(f"⏰ {current_time.strftime('%H:%M:%S')}   🖥️ Server: {Colors.FAIL}OFFLINE{Colors.ENDC} | Ctrl+C exit")
        
        # Flush output
        sys.stdout.flush()