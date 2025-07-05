"""
Data collector module for gathering ccusage data.
"""
import json
import logging
import subprocess
import time
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Dict, Any, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.data_models import SessionData, MonitoringData, ConfigData, ErrorStatus


class DataCollector:
    """Collects data from ccusage command and converts to our data models."""
    
    def __init__(self, config: ConfigData):
        """Initialize DataCollector with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._last_successful_update: Optional[datetime] = None
        self._consecutive_failures = 0
        self._last_fetch_time = 0
        self._cached_data = {"blocks": []}
        
        # Initialize persistent storage for max tokens
        from shared.file_manager import ConfigFileManager
        self._config_manager = ConfigFileManager()
        self._persistent_config = self._config_manager.read_data()
        
        # Initialize max_tokens from persistent storage or scan all history
        if "max_tokens" not in self._persistent_config:
            self.logger.info("No max_tokens found in config - scanning all historical data...")
            self._max_tokens_per_session = self._scan_all_historical_data_for_max_tokens()
        else:
            self._max_tokens_per_session = self._persistent_config.get("max_tokens", 35000)
            self.logger.info(f"Loaded max_tokens from config: {self._max_tokens_per_session:,}")
    
    def collect_data(self) -> MonitoringData:
        """
        Collect data from ccusage command.
        
        Returns:
            MonitoringData object with sessions or error status
        """
        try:
            # Execute ccusage command (use run_ccusage for consistency)
            # Use intelligent fetch strategy for billing period optimization
            config_dict = self.config.to_dict()
            fetch_since = self.determine_fetch_strategy(config_dict, self.config.billing_start_day)
            
            # Execute ccusage with smart fetching
            data = self.run_ccusage(fetch_since)
            if not data or "blocks" not in data:
                self._consecutive_failures += 1
                error_msg = "No blocks data returned from ccusage"
                self.logger.error(f"{error_msg} (consecutive failures: {self._consecutive_failures})")
                raise RuntimeError(error_msg)
            
            # CRITICAL FIX: Filter blocks to billing period only
            blocks = data.get('blocks', [])
            
            # Calculate billing period start
            billing_start_date = self.get_subscription_period_start(self.config.billing_start_day)
            billing_start_utc = datetime.combine(billing_start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            # Filter to current billing period only (excluding gaps)
            period_blocks = []
            for block in blocks:
                if block.get("isGap", False):
                    continue
                try:
                    start_time = datetime.fromisoformat(block["startTime"].replace('Z', '+00:00'))
                    if start_time >= billing_start_utc:
                        period_blocks.append(block)
                except Exception as e:
                    self.logger.warning(f"Failed to parse startTime for block {block.get('id', 'unknown')}: {e}")
                    continue
            
            # Convert filtered blocks to sessions
            sessions = []
            for block in period_blocks:
                try:
                    session = self._parse_ccusage_block(block)
                    sessions.append(session)
                except Exception as e:
                    self.logger.warning(f"Failed to parse block {block.get('id', 'unknown')}: {e}")
                    continue
            
            # Calculate totals
            total_input_tokens = sum(s.input_tokens for s in sessions)
            total_output_tokens = sum(s.output_tokens for s in sessions)
            total_cost_usd = sum(s.cost_usd for s in sessions)
            
            # Count active sessions (sessions without end_time or recent end_time)
            now = datetime.now(timezone.utc)
            active_sessions = 0
            for session in sessions:
                if session.end_time is None:
                    active_sessions += 1
                elif session.end_time and (now - session.end_time).total_seconds() < 300:  # 5 minutes
                    active_sessions += 1
            
            # Calculate max tokens from current sessions
            current_session_max = max([s.total_tokens for s in sessions], default=0)
            
            # Update persistent max_tokens if we found a higher value
            if current_session_max > self._max_tokens_per_session:
                self._max_tokens_per_session = current_session_max
                self._save_max_tokens(current_session_max)
                self.logger.info(f"New maximum tokens found: {current_session_max:,}")
            
            max_tokens = self._max_tokens_per_session
            
            # Update success tracking
            self._last_successful_update = now
            self._consecutive_failures = 0
            self.logger.debug(f"Successfully collected {len(sessions)} sessions, total cost: ${total_cost_usd:.4f}")
            
            # Calculate proper billing period dates
            billing_start_date = self.get_subscription_period_start(self.config.billing_start_day)
            from shared.utils import get_next_renewal_date
            billing_end_date = get_next_renewal_date(self.config.billing_start_day)
            
            # Convert dates to datetime for consistency
            billing_period_start = datetime.combine(billing_start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            billing_period_end = datetime.combine(billing_end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            return MonitoringData(
                current_sessions=sessions,
                total_sessions_this_month=len(sessions),
                total_cost_this_month=total_cost_usd,
                max_tokens_per_session=max_tokens,
                last_update=now,
                billing_period_start=billing_period_start,
                billing_period_end=billing_period_end
            )
            
        except subprocess.TimeoutExpired:
            self._consecutive_failures += 1
            error_msg = "ccusage command timed out after 30 seconds"
            self.logger.error(f"{error_msg} (consecutive failures: {self._consecutive_failures})")
            raise RuntimeError(error_msg)
        except Exception as e:
            self._consecutive_failures += 1
            error_msg = f"Unexpected error in data collection: {e}"
            self.logger.error(f"{error_msg} (consecutive failures: {self._consecutive_failures})")
            raise RuntimeError(error_msg)
    
    def _parse_ccusage_block(self, block: Dict[str, Any]) -> SessionData:
        """
        Parse a single ccusage block into SessionData.
        
        Args:
            block: Dictionary containing block data from ccusage
            
        Returns:
            SessionData object
        """
        # Parse timestamps using correct field names
        start_time = datetime.fromisoformat(block['startTime'].replace('Z', '+00:00'))
        end_time = None
        if 'endTime' in block and block['endTime']:
            end_time = datetime.fromisoformat(block['endTime'].replace('Z', '+00:00'))
        
        # Extract tokens from nested tokenCounts structure
        token_counts = block.get('tokenCounts', {})
        input_tokens = token_counts.get('inputTokens', 0)
        output_tokens = token_counts.get('outputTokens', 0)
        total_tokens = block.get('totalTokens', 0)  # Use provided total, not sum
        
        # Use isActive flag from ccusage (don't calculate based on time)
        is_active = block.get('isActive', False)
        
        return SessionData(
            session_id=block['id'],
            start_time=start_time,
            end_time=end_time,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=block.get('costUSD', 0),
            is_active=is_active
        )
    
    def collect_data_with_retry(self, max_retries: int = 3) -> MonitoringData:
        """
        Collect data with retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            MonitoringData object with sessions
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.collect_data()
            except RuntimeError as e:
                last_error = e
                
                # If this is the last attempt, re-raise the error
                if attempt == max_retries - 1:
                    raise last_error
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                self.logger.info(f"Retrying data collection in {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
        
        # This should never be reached, but just in case
        raise last_error
    
    def get_error_status(self) -> Optional[ErrorStatus]:
        """
        Get current error status.
        
        Returns:
            ErrorStatus if there have been recent failures, None otherwise
        """
        if self._consecutive_failures == 0:
            return None
        
        return ErrorStatus(
            has_error=True,
            error_message=f"Data collection failed {self._consecutive_failures} consecutive times",
            error_code=None,
            last_successful_update=self._last_successful_update,
            consecutive_failures=self._consecutive_failures
        )
    
    @property
    def last_successful_update(self) -> Optional[datetime]:
        """Get timestamp of last successful data collection."""
        return self._last_successful_update
    
    @property
    def consecutive_failures(self) -> int:
        """Get number of consecutive failures."""
        return self._consecutive_failures
    
    def run_ccusage(self, since_date: str = None) -> dict:
        """Execute ccusage command with optional since parameter."""
        command = ["ccusage", "blocks", "-j"]
        if since_date:
            command.extend(["-s", since_date])
        
        # Set up environment for GUI access
        env = os.environ.copy()
        env.update({
            'PATH': '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin',
            'HOME': os.path.expanduser('~'),
            'LANG': 'en_US.UTF-8',
            'DISPLAY': ':0',
            'USER': os.getenv('USER', 'unknown'),
            'TMPDIR': '/tmp'
        })
        
        try:
            # Check if ccusage is available before attempting to run it
            if not self._check_ccusage_available():
                self.logger.error("ccusage command not found in PATH")
                return {"blocks": []}
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True,
                env=env,
                timeout=30
            )
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            self.logger.error("ccusage command timed out")
            return {"blocks": []}
        except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
            self.logger.error(f"ccusage command failed: {e}")
            return {"blocks": []}
    
    def _check_ccusage_available(self) -> bool:
        """
        Check if ccusage command is available in PATH.
        
        Returns:
            bool: True if ccusage is available, False otherwise
        """
        import shutil
        
        try:
            # Check if ccusage is in PATH
            return shutil.which("ccusage") is not None
        except Exception as e:
            self.logger.warning(f"Error checking ccusage availability: {e}")
            return False
    
    def get_subscription_period_start(self, start_day: int) -> date:
        """Calculate billing period start date."""
        today = date.today()
        if today.day >= start_day:
            return today.replace(day=start_day)
        else:
            first_day_of_current_month = today.replace(day=1)
            last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
            return last_day_of_previous_month.replace(day=min(start_day, last_day_of_previous_month.day))
    
    def determine_fetch_strategy(self, config: dict, billing_start_day: int) -> Optional[str]:
        """Determine optimal fetch strategy for ccusage."""
        sub_start_date = self.get_subscription_period_start(billing_start_day)
        sub_start_date_str = sub_start_date.strftime('%Y-%m-%d')
        
        need_full_rescan = config.get("force_recalculate", False)
        need_max_tokens = not config.get("max_tokens") or need_full_rescan
        need_monthly_recalc = need_full_rescan or config.get("monthly_meta", {}).get("period_start") != sub_start_date_str
        
        if need_full_rescan:
            return None  # Fetch everything
        elif need_monthly_recalc:
            return sub_start_date.strftime('%Y%m%d')
        else:
            # Incremental: data from last week or last update
            last_check = config.get("last_incremental_update")
            if last_check:
                since_date = datetime.strptime(last_check, '%Y-%m-%d') - timedelta(days=2)
            else:
                since_date = datetime.now() - timedelta(days=7)
            return since_date.strftime('%Y%m%d')
    
    def find_active_session(self, blocks: List[Dict[str, Any]], now_utc: datetime) -> Optional[Dict[str, Any]]:
        """Find active session based on time range."""
        for block in blocks:
            if block.get("isGap", False):
                continue
            start_time = datetime.fromisoformat(block["startTime"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(block["endTime"].replace('Z', '+00:00'))
            if start_time <= now_utc <= end_time:
                return block
        return None
    
    def filter_unprocessed_sessions(self, blocks: List[Dict[str, Any]], processed_sessions: List[str]) -> List[Dict[str, Any]]:
        """Filter out already processed sessions."""
        return [block for block in blocks if block["id"] not in processed_sessions]
    
    def calculate_new_max_tokens(self, blocks: List[Dict[str, Any]], current_max: int) -> int:
        """Calculate new maximum tokens from blocks."""
        all_tokens = [b.get("totalTokens", 0) for b in blocks if not b.get("isGap", False)]
        if all_tokens:
            new_max = max(all_tokens)
            return max(new_max, current_max)
        return current_max
    
    def should_fetch_new_data(self) -> bool:
        """Check if new data should be fetched based on cache expiration."""
        return time.time() - self._last_fetch_time > self.config.ccusage_fetch_interval_seconds
    
    def _save_max_tokens(self, max_tokens: int):
        """Save max tokens to persistent configuration."""
        try:
            # Update persistent config with new max_tokens
            self._persistent_config["max_tokens"] = max_tokens
            self._persistent_config["last_max_tokens_scan"] = datetime.now().strftime('%Y-%m-%d')
            
            # Save to config file
            self._config_manager.save_config(self._persistent_config)
            self.logger.debug(f"Saved max_tokens {max_tokens:,} to persistent config")
        except Exception as e:
            self.logger.error(f"Failed to save max_tokens to config: {e}")
    
    def get_max_tokens_per_session(self) -> int:
        """Get current maximum tokens per session."""
        return self._max_tokens_per_session
    
    def update_max_tokens_if_higher(self, current_tokens: int) -> bool:
        """
        Update max tokens if current value is higher.
        This is called during active session monitoring for real-time updates.
        
        Args:
            current_tokens: Current token count from active session
            
        Returns:
            True if max_tokens was updated, False otherwise
        """
        if current_tokens > self._max_tokens_per_session:
            self._max_tokens_per_session = current_tokens
            self._save_max_tokens(current_tokens)
            return True
        return False
    
    def force_recalculate_max_tokens(self):
        """Force recalculation of max tokens from historical data."""
        try:
            # Fetch all historical data
            data = self.run_ccusage()  # No since_date = fetch everything
            if not data or "blocks" not in data:
                self.logger.warning("No data available for max tokens recalculation")
                return
            
            blocks = data.get('blocks', [])
            all_tokens = [b.get("totalTokens", 0) for b in blocks if not b.get("isGap", False)]
            
            if all_tokens:
                historical_max = max(all_tokens)
                if historical_max > self._max_tokens_per_session:
                    self._max_tokens_per_session = historical_max
                    self._save_max_tokens(historical_max)
                    self.logger.info(f"Recalculated max_tokens: {historical_max:,}")
                else:
                    self.logger.info(f"Current max_tokens {self._max_tokens_per_session:,} is still valid")
            else:
                self.logger.warning("No token data found in historical blocks")
                
        except Exception as e:
            self.logger.error(f"Failed to recalculate max_tokens: {e}")
    
    def _scan_all_historical_data_for_max_tokens(self) -> int:
        """
        Scan all historical ccusage data to find maximum tokens.
        This is called on first run when no max_tokens is saved.
        
        Returns:
            Maximum tokens found in all historical data, or 35000 as fallback
        """
        try:
            self.logger.info("Scanning all historical data for maximum tokens...")
            
            # Fetch ALL historical data (no since_date parameter)
            data = self.run_ccusage()
            if not data or "blocks" not in data:
                self.logger.warning("No historical data available, using default max_tokens")
                return 35000
            
            blocks = data.get('blocks', [])
            self.logger.info(f"Found {len(blocks)} total blocks in historical data")
            
            # Extract all token counts from non-gap blocks
            all_tokens = []
            for block in blocks:
                if block.get("isGap", False):
                    continue
                total_tokens = block.get("totalTokens", 0)
                if total_tokens > 0:
                    all_tokens.append(total_tokens)
            
            if all_tokens:
                historical_max = max(all_tokens)
                self.logger.info(f"Historical scan complete: found {len(all_tokens)} sessions")
                self.logger.info(f"Maximum tokens from all history: {historical_max:,}")
                
                # Save this max_tokens to persistent config
                self._save_max_tokens(historical_max)
                
                return historical_max
            else:
                self.logger.warning("No token data found in historical blocks, using default")
                # Still save the default to avoid future scans
                self._save_max_tokens(35000)
                return 35000
                
        except Exception as e:
            self.logger.error(f"Failed to scan historical data for max_tokens: {e}")
            self.logger.info("Using default max_tokens value: 35000")
            # Save default to avoid repeating failed scan
            try:
                self._save_max_tokens(35000)
            except Exception:
                pass
            return 35000