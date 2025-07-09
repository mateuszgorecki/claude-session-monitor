#!/usr/bin/env python3
"""
Data models for project name caching system.
"""
import os
import json
import tempfile
from datetime import datetime, timezone
from typing import List, Dict, Optional


class ProjectInfo:
    """Represents information about a project including its git root and aliases.
    
    This class stores metadata about a project for caching purposes, including
    the git root path, derived project name, and any aliases (subdirectories)
    that should resolve to the same project.
    """
    
    def __init__(self, git_root: str) -> None:
        """Initialize ProjectInfo with git root path.
        
        Args:
            git_root: Path to the git root directory of the project
        """
        self.git_root: str = git_root
        self.project_name: str = os.path.basename(git_root)
        self.aliases: List[str] = []
        self.last_accessed: datetime = datetime.now(timezone.utc)
    
    def add_alias(self, alias_path: str) -> None:
        """Add an alias path that should resolve to this project.
        
        Args:
            alias_path: Path to a subdirectory that belongs to this project
        """
        if alias_path not in self.aliases:
            self.aliases.append(alias_path)
            self.last_accessed = datetime.now(timezone.utc)


class ProjectCache:
    """Manages persistent storage and retrieval of project information."""
    
    def __init__(self, cache_file_path: str) -> None:
        """Initialize ProjectCache with file path.
        
        Args:
            cache_file_path: Path to the cache file where project data is stored
        """
        self.cache_file_path = cache_file_path
    
    def load(self) -> Dict[str, ProjectInfo]:
        """Load cached project data from file.
        
        Returns:
            Dictionary mapping project names to ProjectInfo objects,
            or empty dict if file doesn't exist
        """
        try:
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert raw data back to ProjectInfo objects
                result = {}
                for project_name, project_data in data.items():
                    project_info = ProjectInfo(project_data['git_root'])
                    project_info.aliases = project_data.get('aliases', [])
                    # Parse last_accessed time
                    if 'last_accessed' in project_data:
                        project_info.last_accessed = datetime.fromisoformat(project_data['last_accessed'])
                    result[project_name] = project_info
                return result
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return {}
    
    def save(self, data: Dict[str, ProjectInfo]) -> None:
        """Save project data to cache file using atomic operations.
        
        Args:
            data: Dictionary mapping project names to ProjectInfo objects
        """
        # Convert ProjectInfo objects to JSON-serializable format
        serializable_data = {}
        for project_name, project_info in data.items():
            serializable_data[project_name] = {
                'git_root': project_info.git_root,
                'aliases': project_info.aliases,
                'last_accessed': project_info.last_accessed.isoformat()
            }
        
        # Use atomic file operations for thread safety
        self._atomic_save(serializable_data)
    
    def _atomic_save(self, data: Dict) -> None:
        """Atomically save data to cache file using temporary file + rename.
        
        Args:
            data: JSON-serializable data to save
        """
        # Ensure directory exists
        cache_dir = os.path.dirname(self.cache_file_path)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        
        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8', 
            dir=cache_dir,
            prefix=os.path.basename(self.cache_file_path) + '.tmp.',
            delete=False
        ) as temp_file:
            json.dump(data, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())  # Ensure data is written to disk
            temp_file_path = temp_file.name
        
        # Atomic rename to final location
        os.rename(temp_file_path, self.cache_file_path)
    
    def find_project_by_alias(self, alias_path: str) -> Optional[str]:
        """Find project name by alias path.
        
        Args:
            alias_path: Path to search for in project aliases
            
        Returns:
            Project name if found, None otherwise
        """
        data = self.load()
        for project_name, project_info in data.items():
            if alias_path in project_info.aliases:
                return project_name
        return None
    
    def add_alias(self, project_name: str, alias_path: str) -> None:
        """Add an alias to an existing project.
        
        Args:
            project_name: Name of the project to add alias to
            alias_path: Path to add as alias
        """
        data = self.load()
        if project_name in data:
            data[project_name].add_alias(alias_path)
            self.save(data)