"""
Data collector module for gathering ccusage data.
"""
import json
import logging
import subprocess
import time
from datetime import datetime, timezone
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
    
    def collect_data(self) -> MonitoringData:
        """
        Collect data from ccusage command.
        
        Returns:
            MonitoringData object with sessions or error status
        """
        try:
            # Execute ccusage command
            result = subprocess.run(
                ['ccusage', 'blocks', '-j'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if command succeeded
            if result.returncode != 0:
                self._consecutive_failures += 1
                error_msg = f"ccusage command failed with code {result.returncode}: {result.stderr}"
                self.logger.error(f"{error_msg} (consecutive failures: {self._consecutive_failures})")
                raise RuntimeError(error_msg)
            
            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                self._consecutive_failures += 1
                error_msg = f"Failed to parse JSON from ccusage: {e}"
                self.logger.error(f"{error_msg} (consecutive failures: {self._consecutive_failures})")
                raise RuntimeError(error_msg)
            
            # Convert blocks to sessions
            sessions = []
            blocks = data.get('blocks', [])
            
            for block in blocks:
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
            
            max_tokens = max([s.total_tokens for s in sessions], default=0)
            
            # Update success tracking
            self._last_successful_update = now
            self._consecutive_failures = 0
            self.logger.debug(f"Successfully collected {len(sessions)} sessions, total cost: ${total_cost_usd:.4f}")
            
            return MonitoringData(
                current_sessions=sessions,
                total_sessions_this_month=len(sessions),
                total_cost_this_month=total_cost_usd,
                max_tokens_per_session=max_tokens,
                last_update=now,
                billing_period_start=now.replace(day=1),
                billing_period_end=now.replace(day=28)
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
        # Parse timestamps
        start_time = datetime.fromisoformat(block['start_time'].replace('Z', '+00:00'))
        end_time = None
        if 'end_time' in block and block['end_time']:
            end_time = datetime.fromisoformat(block['end_time'].replace('Z', '+00:00'))
        
        # Calculate total tokens
        input_tokens = block['input_tokens']
        output_tokens = block['output_tokens']
        total_tokens = input_tokens + output_tokens
        
        # Determine if session is active (no end_time or recent end_time)
        is_active = end_time is None
        if end_time is not None:
            now = datetime.now(timezone.utc)
            is_active = (now - end_time).total_seconds() < 300  # 5 minutes
        
        return SessionData(
            session_id=block['id'],
            start_time=start_time,
            end_time=end_time,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=block['cost'],
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