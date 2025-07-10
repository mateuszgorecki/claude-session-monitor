import json
import os
import subprocess
import threading
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add project root to path so we can import shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.shared.project_name_resolver import ProjectNameResolver
from src.shared.utils import get_project_cache_file_path


class HookLogger:
    """Thread-safe logger for Claude Code hook events.
    
    Provides atomic file operations for logging hook events in JSON format.
    Each log entry includes a UTC timestamp and the provided event data.
    """
    
    def __init__(self, log_file_path: str):
        """Initialize the hook logger.
        
        Args:
            log_file_path: Path to the log file where events will be written
        """
        self.log_file_path = log_file_path
        self._lock = threading.Lock()
    
    def log_event(self, event_data: Dict[str, Any]) -> None:
        """Log an event to the log file in JSON format.
        
        Thread-safe method that appends the event data to the log file.
        Automatically creates the directory if it doesn't exist.
        
        Args:
            event_data: Dictionary containing event information
        """
        # Add timestamp to event data (using timezone-aware datetime)
        event_with_timestamp = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **event_data
        }
        
        # Ensure directory exists
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Thread-safe file writing
        with self._lock:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                json.dump(event_with_timestamp, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')


def find_project_root(start_path: Optional[str] = None) -> str:
    """Find the project root directory by looking for common project markers.
    
    This function tries multiple strategies to find the true project root:
    1. Git root directory (most reliable)
    2. Directory containing common project files (.git, package.json, pyproject.toml, etc.)
    3. Falls back to current directory basename
    
    Args:
        start_path: Directory to start searching from (defaults to current directory)
        
    Returns:
        Project name (basename of project root directory)
    """
    if start_path is None:
        start_path = os.getcwd()
    
    # Strategy 1: Try to find git root
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=start_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_root = result.stdout.strip()
            if git_root:
                return os.path.basename(git_root)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass
    
    # Strategy 2: Look for common project markers
    project_markers = [
        '.git',
        'package.json',
        'pyproject.toml',
        'setup.py',
        'Cargo.toml',
        'pom.xml',
        'build.gradle',
        'go.mod',
        'composer.json',
        'requirements.txt',
        'Pipfile',
        'poetry.lock',
        'yarn.lock',
        'package-lock.json',
        '.gitignore'
    ]
    
    current_dir = os.path.abspath(start_path)
    root_dir = os.path.abspath(os.sep)
    
    while current_dir != root_dir:
        for marker in project_markers:
            marker_path = os.path.join(current_dir, marker)
            if os.path.exists(marker_path):
                return os.path.basename(current_dir)
        
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # Reached root
            break
        current_dir = parent_dir
    
    # Strategy 3: Fallback to current directory basename
    return os.path.basename(start_path)


def get_project_name_cached(start_path: Optional[str] = None) -> str:
    """
    Get project name using cached ProjectNameResolver with intelligent project detection.
    
    This function provides a cache-first approach to project name resolution,
    using the ProjectNameResolver system with adaptive learning and fallback mechanisms.
    
    Args:
        start_path: Directory to start resolving from (defaults to current directory)
        
    Returns:
        Project name string (never None, always returns some value)
    """
    # Use current directory as default if no path provided
    if not start_path:
        start_path = os.getcwd()
    
    try:
        # Initialize resolver with standard cache file path
        cache_file_path = get_project_cache_file_path()
        resolver = ProjectNameResolver(cache_file_path)
        
        # Use resolver to get project name
        return resolver.resolve_project_name(start_path)
    except Exception:
        # Fallback to basename if resolver fails
        return os.path.basename(start_path) if start_path else 'unknown'