#!/usr/bin/env python3
"""
Session Activity Tracker for Claude session monitor.
Tracks activity sessions from Claude Code hooks and manages session lifecycle.
"""

import os
import logging
import glob
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Set
from pathlib import Path

from daemon.hook_log_parser import HookLogParser
from shared.data_models import ActivitySessionData, ActivitySessionStatus
from shared.constants import HOOK_LOG_DIR, HOOK_LOG_FILE_PATTERN, HOOK_LOG_RETENTION_DAYS


class SessionActivityTracker:
    """Tracks activity sessions from Claude Code hook logs.
    
    This class manages the lifecycle of activity sessions by reading hook log files,
    parsing them into ActivitySessionData objects, and providing access to session
    information with caching and performance optimizations.
    """
    
    def __init__(self, enable_background_updates: bool = False):
        """Initialize the session activity tracker.
        
        Args:
            enable_background_updates: If True, start background thread for file watching
        """
        self.logger = logging.getLogger(__name__)
        self.parser = HookLogParser()
        self._active_sessions: List[ActivitySessionData] = []
        self._last_cache_update: Optional[datetime] = None
        self._file_modification_times: Dict[str, float] = {}
        self._processed_files: Set[str] = set()
        self._session_lock = threading.RLock()
        self._background_thread: Optional[threading.Thread] = None
        self._stop_background = threading.Event()
        
        # Performance metrics
        self._stats = {
            'total_files_processed': 0,
            'total_sessions_parsed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'last_update_duration': 0.0
        }
        
        if enable_background_updates:
            self.start_background_updates()
    
    def get_active_sessions(self) -> List[ActivitySessionData]:
        """Get list of currently active sessions.
        
        Returns:
            List of ActivitySessionData objects for active sessions
        """
        with self._session_lock:
            return [session for session in self._active_sessions 
                    if session.status == ActivitySessionStatus.ACTIVE.value]
    
    def update_from_log_files(self, force_update: bool = False) -> bool:
        """Update session data from hook log files.
        
        Args:
            force_update: If True, force update regardless of cache validity
        
        Returns:
            True if update was successful, False otherwise
        """
        start_time = time.time()
        
        try:
            log_files = self._discover_log_files()
            
            if force_update or not self._is_cache_valid(log_files):
                self._stats['cache_misses'] += 1
                
                with self._session_lock:
                    all_sessions = []
                    processed_count = 0
                    
                    # When cache is invalid, reprocess all files to get latest events
                    for log_file in log_files:
                        sessions = self._process_log_file(log_file)
                        all_sessions.extend(sessions)
                        self._processed_files.add(log_file)
                        processed_count += 1
                    
                    # Merge sessions by session_id to consolidate events
                    if all_sessions or force_update:
                        self._active_sessions = self._merge_sessions(all_sessions)
                        self._last_cache_update = datetime.now()
                        
                        self._stats['total_files_processed'] += processed_count
                        self._stats['total_sessions_parsed'] += len(all_sessions)
                    
                    self.logger.debug(f"Updated {len(self._active_sessions)} sessions from {processed_count} new log files")
            else:
                self._stats['cache_hits'] += 1
                self.logger.debug("Using cached session data")
            
            self._stats['last_update_duration'] = time.time() - start_time
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update from log files: {e}")
            return False
    
    def get_sessions_for_period(self, start_date: datetime, end_date: datetime) -> List[ActivitySessionData]:
        """Get sessions within a specific time period.
        
        Args:
            start_date: Start of the time period
            end_date: End of the time period
            
        Returns:
            List of ActivitySessionData objects within the period
        """
        filtered_sessions = []
        
        for session in self._active_sessions:
            # Check if session overlaps with the requested period
            session_start = session.start_time
            session_end = session.end_time or datetime.now(timezone.utc)
            
            if (session_start <= end_date and session_end >= start_date):
                filtered_sessions.append(session)
        
        return filtered_sessions
    
    def get_session_by_id(self, session_id: str) -> Optional[ActivitySessionData]:
        """Get a specific session by ID.
        
        Args:
            session_id: The session ID to search for
            
        Returns:
            ActivitySessionData object if found, None otherwise
        """
        for session in self._active_sessions:
            if session.session_id == session_id:
                return session
        return None
    
    def get_session_by_project(self, project_name: str) -> Optional[ActivitySessionData]:
        """Get a specific session by project name.
        
        Args:
            project_name: The project name to search for
            
        Returns:
            ActivitySessionData object if found, None otherwise
        """
        for session in self._active_sessions:
            if session.project_name == project_name:
                return session
        return None
    
    def _discover_log_files(self) -> List[str]:
        """Discover hook log files in the configured directory.
        
        Returns:
            List of absolute paths to hook log files
        """
        log_dir = os.path.expanduser(HOOK_LOG_DIR)
        if not os.path.exists(log_dir):
            self.logger.debug(f"Hook log directory does not exist: {log_dir}")
            return []
        
        # Check for the single hook log file
        log_file_path = os.path.join(log_dir, HOOK_LOG_FILE_PATTERN)
        
        if os.path.exists(log_file_path):
            log_files = [log_file_path]
        else:
            log_files = []
        log_files.sort()  # Sort chronologically
        
        self.logger.debug(f"Discovered {len(log_files)} log files in {log_dir}")
        return log_files
    
    def _process_log_file(self, file_path: str) -> List[ActivitySessionData]:
        """Process a single log file using the hook log parser.
        
        Args:
            file_path: Path to the log file to process
            
        Returns:
            List of ActivitySessionData objects from the file
        """
        return self.parser.parse_log_file(file_path)
    
    def _merge_sessions(self, sessions: List[ActivitySessionData]) -> List[ActivitySessionData]:
        """Merge sessions by project_name and calculate smart status based on event history.
        
        Groups events by project_name and uses smart detection to determine session status
        based on the most recent event type and timing.
        
        Args:
            sessions: List of ActivitySessionData objects to merge
            
        Returns:
            List of merged ActivitySessionData objects with smart status
        """
        # Group sessions by project_name
        session_groups: Dict[str, List[ActivitySessionData]] = {}
        
        for session in sessions:
            project_name = session.project_name
            if project_name not in session_groups:
                session_groups[project_name] = []
            session_groups[project_name].append(session)
        
        merged_sessions = []
        
        for project_name, events in session_groups.items():
            # Sort events by timestamp to find earliest and latest
            sorted_events = sorted(events, key=lambda e: e.start_time)
            first_event = sorted_events[0]
            last_event = sorted_events[-1]
            
            # Calculate smart status based on event history
            smart_status = ActivitySessionData.calculate_smart_status(events)
            
            # Create merged session with smart status
            merged_session = ActivitySessionData(
                project_name=project_name,
                session_id=first_event.session_id,  # Keep first session_id for reference
                start_time=first_event.start_time,  # First event time as session start
                status=smart_status,
                event_type=last_event.event_type,  # Most recent event type
                end_time=last_event.start_time if smart_status == ActivitySessionStatus.INACTIVE.value else None,
                metadata={
                    'event_count': len(events),
                    'last_event_time': last_event.start_time.isoformat(),
                    'events': [{'type': e.event_type, 'time': e.start_time.isoformat()} for e in sorted_events]
                }
            )
            
            merged_sessions.append(merged_session)
        
        return merged_sessions
    
    def start_background_updates(self, update_interval: float = 5.0) -> None:
        """Start background thread for automatic file watching and updates.
        
        Args:
            update_interval: Interval in seconds between update checks
        """
        if self._background_thread and self._background_thread.is_alive():
            self.logger.warning("Background updates already running")
            return
        
        self._stop_background.clear()
        self._background_thread = threading.Thread(
            target=self._background_update_worker,
            args=(update_interval,),
            daemon=True,
            name="SessionActivityTracker-Background"
        )
        self._background_thread.start()
        self.logger.info(f"Started background updates with {update_interval}s interval")
    
    def stop_background_updates(self) -> None:
        """Stop the background update thread."""
        if self._background_thread and self._background_thread.is_alive():
            self._stop_background.set()
            self._background_thread.join(timeout=5.0)
            self.logger.info("Stopped background updates")
    
    def _background_update_worker(self, update_interval: float) -> None:
        """Background worker that periodically checks for file updates."""
        while not self._stop_background.wait(update_interval):
            try:
                self.update_from_log_files()
            except Exception as e:
                self.logger.error(f"Error in background update: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance and usage statistics.
        
        Returns:
            Dictionary containing various statistics
        """
        with self._session_lock:
            stats = self._stats.copy()
            stats.update({
                'active_sessions_count': len(self.get_active_sessions()),
                'total_sessions_count': len(self._active_sessions),
                'processed_files_count': len(self._processed_files),
                'cache_hit_ratio': (
                    self._stats['cache_hits'] / max(1, self._stats['cache_hits'] + self._stats['cache_misses'])
                ) * 100,
                'background_updates_enabled': self._background_thread is not None and self._background_thread.is_alive()
            })
        return stats
    
    def get_sessions_by_status(self, status: str) -> List[ActivitySessionData]:
        """Get sessions filtered by status.
        
        Args:
            status: Session status to filter by (ACTIVE, WAITING, STOPPED)
            
        Returns:
            List of sessions with the specified status
        """
        with self._session_lock:
            return [session for session in self._active_sessions if session.status == status]
    
    def get_recent_sessions(self, hours: int = 24) -> List[ActivitySessionData]:
        """Get sessions from the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent sessions
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        with self._session_lock:
            return [
                session for session in self._active_sessions 
                if session.start_time >= cutoff_time
            ]
    
    def clear_cache(self) -> None:
        """Clear all cached data and force reload on next update."""
        with self._session_lock:
            self._processed_files.clear()
            self._file_modification_times.clear()
            self._last_cache_update = None
            self.logger.info("Cleared all cache data")
    
    def _is_cache_valid(self, log_files: List[str]) -> bool:
        """Check if the current cache is still valid.
        
        Args:
            log_files: List of log file paths to check
            
        Returns:
            True if cache is valid, False if needs updating
        """
        if self._last_cache_update is None:
            return False
        
        # Check if any log file has been modified since last cache update
        for file_path in log_files:
            try:
                current_mtime = os.path.getmtime(file_path)
                cached_mtime = self._file_modification_times.get(file_path, 0)
                
                if current_mtime > cached_mtime:
                    # Update cached modification time
                    self._file_modification_times[file_path] = current_mtime
                    return False
                    
            except OSError:
                # File might have been deleted, consider cache invalid
                return False
        
        return True
    
    def cleanup_old_sessions(self, retention_days: Optional[int] = None) -> None:
        """Clean up sessions older than the retention period.
        
        Args:
            retention_days: Number of days to retain session data. 
                          If None, uses HOOK_LOG_RETENTION_DAYS from constants.
        """
        if retention_days is None:
            retention_days = HOOK_LOG_RETENTION_DAYS
            
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        with self._session_lock:
            initial_count = len(self._active_sessions)
            self._active_sessions = [
                session for session in self._active_sessions
                if session.start_time >= cutoff_date
            ]
            
            removed_count = initial_count - len(self._active_sessions)
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old sessions (older than {retention_days} days)")
    
    def cleanup_completed_billing_sessions(self) -> None:
        """Clean up activity sessions that are no longer part of active 5-hour billing window.
        
        This method removes sessions older than 5 hours from memory and clears the log file
        if all sessions are outside the billing window. This prevents accumulation of
        old activity data that's no longer relevant for billing session monitoring.
        """
        from datetime import datetime, timezone
        
        # Define 5-hour billing session window
        BILLING_SESSION_HOURS = 5
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=BILLING_SESSION_HOURS)
        
        with self._session_lock:
            # Separate recent sessions (within 5h) from old sessions (outside 5h)
            recent_sessions = [
                session for session in self._active_sessions
                if session.start_time >= cutoff_time
            ]
            
            old_sessions = [
                session for session in self._active_sessions
                if session.start_time < cutoff_time
            ]
            
            # If there are old sessions to remove
            if old_sessions:
                # Update active sessions to only include recent ones
                self._active_sessions = recent_sessions
                
                self.logger.info(f"Removed {len(old_sessions)} sessions outside 5h billing window")
                
                # If ALL sessions were old (no recent sessions), clear the log file completely
                if not recent_sessions:
                    log_dir = os.path.expanduser(HOOK_LOG_DIR)
                    log_file_path = os.path.join(log_dir, HOOK_LOG_FILE_PATTERN)
                    
                    try:
                        if os.path.exists(log_file_path):
                            # Clear the file content (truncate to 0 bytes)
                            with open(log_file_path, 'w') as f:
                                pass  # Just open and close to truncate
                            
                            self.logger.info(f"Cleared activity log file - all sessions outside 5h billing window")
                            
                            # Clear file modification cache as well
                            self._file_modification_times.clear()
                            self._last_cache_update = None
                            
                    except Exception as e:
                        self.logger.error(f"Failed to clear activity log file: {e}")
    
    def __del__(self):
        """Cleanup when tracker is destroyed."""
        try:
            self.stop_background_updates()
        except Exception:
            pass  # Ignore errors during cleanup