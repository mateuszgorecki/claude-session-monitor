#!/usr/bin/env python3
"""
ProjectNameResolver - Core project name resolution logic with caching and git integration.

This module provides the main orchestration logic for project name resolution,
combining cache lookup, git detection, and fallback mechanisms.
"""

import os
from typing import Optional

from .project_models import ProjectInfo, ProjectCache
from .git_resolver import GitResolver


class ProjectNameResolver:
    """
    Core project name resolver with intelligent caching and git integration.
    
    Provides stable project identification across different working directories
    by combining cache lookup, git repository detection, and fallback mechanisms.
    """
    
    def __init__(self, cache_file_path: str) -> None:
        """
        Initialize ProjectNameResolver with cache file path.
        
        Args:
            cache_file_path: Path to the cache file for persistent storage
        """
        self.cache = ProjectCache(cache_file_path)
        self.git_resolver = GitResolver()
    
    def resolve_project_name(self, cwd: str) -> str:
        """
        Resolve project name for the given working directory.
        
        This method implements the core logic:
        1. Check cache for direct path match or alias match
        2. If cache miss, use git detection to find project
        3. Update cache with new discovery and create aliases
        4. Fall back to basename if git detection fails
        
        Args:
            cwd: Current working directory to resolve project name for
            
        Returns:
            Project name string (never None, always returns some value)
        """
        # Handle None or empty path
        if not cwd:
            return 'unknown'
        
        # First, try cache lookup (fast path)
        cached_result = self._lookup_in_cache(cwd)
        if cached_result:
            return cached_result
        
        # Cache miss - try git detection (slow path)
        git_root = self.git_resolver.get_git_root(cwd)
        if git_root:
            project_name = self.git_resolver.get_project_name_from_git_root(git_root)
            self._update_cache(cwd, git_root, project_name)
            return project_name
        
        # Git detection failed - fall back to basename
        return os.path.basename(cwd) if cwd else 'unknown'
    
    def _lookup_in_cache(self, cwd: str) -> Optional[str]:
        """
        Look up project name in cache for the given path.
        
        Checks both direct project matches and alias matches.
        
        Args:
            cwd: Current working directory to look up
            
        Returns:
            Project name if found in cache, None otherwise
        """
        cache_data = self.cache.load()
        
        # Check for direct git root match
        for project_name, project_info in cache_data.items():
            if project_info.git_root == cwd:
                return project_name
        
        # Check for alias match
        return self.cache.find_project_by_alias(cwd)
    
    def _update_cache(self, cwd: str, git_root: str, project_name: str) -> None:
        """
        Update cache with new project discovery.
        
        Creates new project entry or updates existing one, and creates
        alias if the current path is a subdirectory of git root.
        
        Args:
            cwd: Current working directory that was resolved
            git_root: Git repository root path
            project_name: Resolved project name
        """
        cache_data = self.cache.load()
        
        # Create or update project entry
        if project_name not in cache_data:
            cache_data[project_name] = ProjectInfo(git_root)
        
        # Create alias if cwd is a subdirectory of git root
        if cwd != git_root:
            cache_data[project_name].add_alias(cwd)
        
        # Save updated cache
        self.cache.save(cache_data)