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

    def play_audio_signal(self):
        """Play a short audio signal using system beep."""
        try:
            # Use osascript for better SSH compatibility (plays on host)
            subprocess.run(['osascript', '-e', 'beep 1'], 
                          check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # Fallback to afplay for local sessions
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], 
                              check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                # Final fallback to terminal bell
                try:
                    print('\a', end='', flush=True)
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

    def calculate_session_stats(self, total_monthly_sessions: int, current_sessions: int,
                              days_in_period: int, days_remaining: int) -> Dict[str, Any]:
        """
        Calculate session usage statistics.
        
        Args:
            total_monthly_sessions: Total sessions allowed per month
            current_sessions: Sessions used so far
            days_in_period: Total days in billing period
            days_remaining: Days remaining in period
            
        Returns:
            Dictionary with session statistics
        """
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
            'avg_sessions_per_day': avg_sessions_per_day
        }

    def render_active_session_display(self, monitoring_data: MonitoringData, 
                                    active_session: SessionData):
        """
        Render display for when there's an active session.
        
        Args:
            monitoring_data: Current monitoring data
            active_session: The active session to display
        """
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
        print(f"\n{Colors.WARNING}Waiting for a new session to start...{Colors.ENDC}\n")
        print(f"Saved max tokens: {monitoring_data.max_tokens_per_session:,}")
        
        # Show current subscription period start
        period_start = monitoring_data.billing_period_start.strftime('%Y-%m-%d')
        print(f"Current subscription period started: {period_start}\n")

    def render_footer(self, current_time: datetime, session_stats: Dict[str, Any],
                     days_remaining: int, total_cost: float, daemon_version: Optional[str] = None):
        """
        Render footer with session statistics and cost.
        
        Args:
            current_time: Current local time
            session_stats: Session usage statistics
            days_remaining: Days remaining in billing period
            total_cost: Total cost for the month
            daemon_version: Daemon version if available
        """
        print("=" * 60)
        
        # Footer line 1: Time, sessions, cost
        footer_line1 = (
            f"⏰ {current_time.strftime('%H:%M:%S')}   "
            f"🗓️ Sessions: {Colors.BOLD}{session_stats['sessions_used']} used, "
            f"{session_stats['sessions_left']} left{Colors.ENDC} | "
            f"💰 Cost (mo): ${total_cost:.2f}"
        )
        
        # Footer line 2: Shortened for better readability
        version_info = daemon_version if daemon_version else "unknown"
        footer_line2 = (
            f"  └─ ⏳ {days_remaining}d left "
            f"(avg {session_stats['avg_sessions_per_day']:.1f}/day) | "
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
        Check for activity session status changes and play audio signal when transitioning to WAITING_FOR_USER.
        
        Args:
            activity_sessions: Current list of activity sessions
        """
        # Track current session statuses
        current_statuses = {}
        for session in activity_sessions:
            session_key = f"{session.project_name}_{session.session_id}"
            current_statuses[session_key] = session.status
        
        # Check for status changes that should trigger audio signal
        for session_key, current_status in current_statuses.items():
            if session_key in self._previous_activity_session_statuses:
                previous_status = self._previous_activity_session_statuses[session_key]
                # Play audio signal when transitioning from ACTIVE to WAITING_FOR_USER
                if (previous_status == "ACTIVE" and current_status == "WAITING_FOR_USER"):
                    self.play_audio_signal()
                    break  # Only play once per update cycle
        
        # Update previous statuses
        self._previous_activity_session_statuses = current_statuses.copy()

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
        
        # Clear screen on first run or when activity sessions change, otherwise just move to top
        if not self._screen_cleared or sessions_changed:
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
        
        # Calculate session statistics
        session_stats = self.calculate_session_stats(
            self.total_monthly_sessions,
            monitoring_data.total_sessions_this_month,
            days_in_period,
            days_remaining
        )
        
        # Check for active session
        active_session = self.find_active_session(monitoring_data)
        
        # Determine current session state
        current_session_state = "active" if active_session else "waiting"
        
        # Check if state changed from active to waiting and play audio signal
        if (self._previous_session_state == "active" and 
            current_session_state == "waiting"):
            self.play_audio_signal()
        
        # Check for activity session status changes and play audio signal
        activity_sessions = getattr(monitoring_data, 'activity_sessions', None) or []
        self._check_activity_session_changes(activity_sessions)
        
        # Update previous session state
        self._previous_session_state = current_session_state
        
        if active_session:
            # Render active session display
            self.render_active_session_display(monitoring_data, active_session)
        else:
            # Render waiting display
            self.render_waiting_display(monitoring_data)
        
        # Render activity sessions if available
        activity_sessions = getattr(monitoring_data, 'activity_sessions', None) or []
        self._render_activity_sessions(activity_sessions)
        
        # Render footer
        self.render_footer(current_time, session_stats, days_remaining, 
                          monitoring_data.total_cost_this_month, monitoring_data.daemon_version)
        
        # Flush output
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