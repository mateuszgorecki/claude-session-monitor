#!/usr/bin/env python3
"""
GitResolver - Git repository detection and project name extraction.

This module provides functionality to detect git repository roots and extract
meaningful project names from git repositories.
"""

import os
import subprocess
from typing import Optional


class GitResolver:
    """
    Handles git repository detection and project name extraction.
    
    Provides methods to:
    - Detect git repository root from any subdirectory
    - Extract project names from git root paths
    - Handle errors gracefully with fallback mechanisms
    """
    
    def get_git_root(self, cwd: str) -> Optional[str]:
        """
        Get the git repository root for the given directory.
        
        Args:
            cwd: Current working directory or any path within a git repository
            
        Returns:
            Absolute path to git repository root, or None if not in a git repo
            
        Raises:
            No exceptions - handles all errors gracefully
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,  # 5 second timeout
                check=True
            )
            
            git_root = result.stdout.strip()
            
            # Validate the result is a valid directory
            if git_root and os.path.isdir(git_root):
                return os.path.abspath(git_root)
            
            return None
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Handle all git command failures gracefully
            return None
    
    def get_project_name_from_git_root(self, git_root: str) -> str:
        """
        Extract project name from git repository root path.
        
        Args:
            git_root: Absolute path to git repository root
            
        Returns:
            Project name extracted from the git root path
            
        Examples:
            '/Users/user/projects/my-project' -> 'my-project'
            '/path/to/project/' -> 'project'
            '/' -> 'root'
        """
        if not git_root:
            return 'unknown'
        
        # Handle root directory edge case first
        if git_root.rstrip('/') == '':
            return 'root'
        
        # Remove trailing slashes and normalize path
        normalized_path = os.path.normpath(git_root.rstrip('/'))
        
        # Extract basename (last component of path)
        project_name = os.path.basename(normalized_path)
        
        # Fallback for empty basename
        if not project_name:
            return 'unknown'
            
        return project_name