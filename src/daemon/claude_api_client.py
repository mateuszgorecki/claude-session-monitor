"""
Direct Claude API client as an alternative to ccusage subprocess calls.
This avoids fork/subprocess issues in launchd daemons.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


class ClaudeAPIClient:
    """
    Direct API client for Claude usage data.
    This is an alternative to using the ccusage CLI tool.
    """
    
    def __init__(self):
        """Initialize the API client."""
        self.logger = logging.getLogger(__name__)
        self._session = None
        self._auth_token = None
        self._base_url = "https://api.anthropic.com"  # Update with actual API URL
        self._cache = {}
        self._cache_ttl = 10  # seconds
        
        # Try to load authentication from ccusage config
        self._load_auth_from_ccusage()
        
    def _load_auth_from_ccusage(self):
        """
        Try to load authentication details from ccusage configuration.
        The ccusage tool likely stores auth tokens that we can reuse.
        """
        try:
            # Common locations for ccusage config
            config_paths = [
                Path.home() / ".config" / "ccusage" / "config.json",
                Path.home() / ".ccusage" / "config.json",
                Path.home() / ".ccusage.json",
            ]
            
            for config_path in config_paths:
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        # Look for auth token in various possible fields
                        self._auth_token = (
                            config.get('token') or 
                            config.get('auth_token') or 
                            config.get('api_key') or
                            config.get('apiKey')
                        )
                        if self._auth_token:
                            self.logger.info(f"Loaded auth token from {config_path}")
                            break
                            
            if not self._auth_token:
                # Try environment variables
                self._auth_token = (
                    os.environ.get('CLAUDE_API_KEY') or
                    os.environ.get('ANTHROPIC_API_KEY') or
                    os.environ.get('CCUSAGE_TOKEN')
                )
                if self._auth_token:
                    self.logger.info("Loaded auth token from environment")
                    
        except Exception as e:
            self.logger.warning(f"Failed to load auth from ccusage config: {e}")
            
    def _get_session(self) -> requests.Session:
        """Get or create HTTP session."""
        if requests is None:
            raise RuntimeError("requests library is not installed")
            
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'claude-monitor-daemon/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            if self._auth_token:
                self._session.headers['Authorization'] = f'Bearer {self._auth_token}'
                
        return self._session
        
    def fetch_usage_blocks(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch usage blocks from the API.
        
        Args:
            since_date: Optional date string (YYYYMMDD format) to fetch data since
            
        Returns:
            Dictionary with blocks data, matching ccusage format
        """
        # Check cache first
        cache_key = f"blocks_{since_date or 'all'}"
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                self.logger.debug(f"Returning cached data for {cache_key}")
                return cached_data
                
        # If we don't have requests library, fall back to subprocess
        if requests is None:
            self.logger.warning("requests library not available, falling back to subprocess")
            return self._fallback_to_subprocess(since_date)
            
        # If we don't have auth token, fall back to subprocess
        if not self._auth_token:
            self.logger.warning("No auth token available, falling back to subprocess")
            return self._fallback_to_subprocess(since_date)
            
        try:
            session = self._get_session()
            
            # Build request parameters
            params = {}
            if since_date:
                # Convert YYYYMMDD to ISO format
                since_dt = datetime.strptime(since_date, "%Y%m%d")
                params['since'] = since_dt.isoformat() + 'Z'
                
            # Make API request
            response = session.get(
                f"{self._base_url}/usage/blocks",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Cache successful response
            self._cache[cache_key] = (data, time.time())
            
            return data
            
        except Exception as e:
            self.logger.error(f"API request failed: {e}")
            # Fall back to subprocess on API failure
            return self._fallback_to_subprocess(since_date)
            
    def _fallback_to_subprocess(self, since_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fall back to using subprocess when API is not available.
        This uses the subprocess pool to avoid fork issues.
        """
        try:
            from .subprocess_pool import run_ccusage_pooled
            return run_ccusage_pooled(since_date)
        except Exception as e:
            self.logger.error(f"Subprocess fallback failed: {e}")
            return {"blocks": []}
            
    def close(self):
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None


# Global API client instance
_api_client = None


def get_api_client() -> ClaudeAPIClient:
    """Get or create the global API client."""
    global _api_client
    if _api_client is None:
        _api_client = ClaudeAPIClient()
    return _api_client


def fetch_usage_data(since_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch usage data using the most appropriate method.
    
    This function tries to use the API client first, then falls back
    to subprocess pool if needed.
    
    Args:
        since_date: Optional date string (YYYYMMDD format)
        
    Returns:
        Dictionary with usage blocks data
    """
    client = get_api_client()
    return client.fetch_usage_blocks(since_date)