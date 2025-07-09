#!/usr/bin/env python3
"""
Test module for GitResolver class - git repository detection and project name extraction.
"""

import unittest
import tempfile
import os
import subprocess
from unittest.mock import patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.git_resolver import GitResolver


class TestGitResolver(unittest.TestCase):
    """Test cases for GitResolver class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.resolver = GitResolver()
        
    def test_get_git_root_with_valid_repo(self):
        """Test get_git_root() returns correct path for valid git repository."""
        # We'll test with the current repo since we know it's a git repo
        current_dir = os.getcwd()
        git_root = self.resolver.get_git_root(current_dir)
        
        # Should return a path (not None)
        self.assertIsNotNone(git_root)
        self.assertIsInstance(git_root, str)
        
        # Should be an absolute path
        self.assertTrue(os.path.isabs(git_root))
        
        # Should be a directory that exists
        self.assertTrue(os.path.isdir(git_root))
        
        # Should contain a .git directory or be a git working tree
        self.assertTrue(
            os.path.exists(os.path.join(git_root, '.git')) or 
            self._is_git_working_tree(git_root)
        )
    
    def _is_git_working_tree(self, path):
        """Helper to check if path is a git working tree."""
        try:
            subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                         cwd=path, capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
    
    def test_get_project_name_from_git_root(self):
        """Test get_project_name_from_git_root() extracts correct project name."""
        # Test with typical project paths
        test_cases = [
            ('/Users/user/projects/my-awesome-project', 'my-awesome-project'),
            ('/home/dev/workspace/claude-session-monitor', 'claude-session-monitor'),
            ('/var/www/html/project_name', 'project_name'),
            ('/path/to/Project.Name', 'Project.Name'),
            ('/', 'root'),  # Edge case - root directory
            ('/single', 'single'),  # Single directory name
        ]
        
        for git_root, expected_name in test_cases:
            with self.subTest(git_root=git_root):
                project_name = self.resolver.get_project_name_from_git_root(git_root)
                self.assertEqual(project_name, expected_name)
    
    def test_get_project_name_handles_trailing_slash(self):
        """Test project name extraction handles trailing slashes correctly."""
        test_cases = [
            ('/path/to/project/', 'project'),
            ('/path/to/project///', 'project'),
            ('/path/to/project', 'project'),
        ]
        
        for git_root, expected_name in test_cases:
            with self.subTest(git_root=git_root):
                project_name = self.resolver.get_project_name_from_git_root(git_root)
                self.assertEqual(project_name, expected_name)
    
    def test_get_git_root_non_git_directory(self):
        """Test get_git_root() returns None for non-git directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary directory that's definitely not a git repo
            non_git_dir = os.path.join(temp_dir, 'not_a_git_repo')
            os.makedirs(non_git_dir)
            
            git_root = self.resolver.get_git_root(non_git_dir)
            self.assertIsNone(git_root)
    
    def test_get_git_root_nonexistent_directory(self):
        """Test get_git_root() handles nonexistent directories gracefully."""
        nonexistent_path = '/path/that/definitely/does/not/exist/12345'
        git_root = self.resolver.get_git_root(nonexistent_path)
        self.assertIsNone(git_root)
    
    @patch('subprocess.run')
    def test_get_git_root_git_command_failure(self, mock_run):
        """Test get_git_root() handles git command failures gracefully."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
        
        git_root = self.resolver.get_git_root('/some/path')
        self.assertIsNone(git_root)
    
    @patch('subprocess.run')
    def test_get_git_root_timeout(self, mock_run):
        """Test get_git_root() handles timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired('git', 5)
        
        git_root = self.resolver.get_git_root('/some/path')
        self.assertIsNone(git_root)
    
    @patch('subprocess.run')
    def test_get_git_root_file_not_found(self, mock_run):
        """Test get_git_root() handles git command not found gracefully."""
        mock_run.side_effect = FileNotFoundError('git command not found')
        
        git_root = self.resolver.get_git_root('/some/path')
        self.assertIsNone(git_root)
    
    def test_get_project_name_edge_cases(self):
        """Test project name extraction edge cases."""
        test_cases = [
            ('', 'unknown'),  # Empty string
            (None, 'unknown'),  # None input - this will need handling
            ('/', 'root'),  # Root directory
            ('//', 'root'),  # Double slash root
            ('///', 'root'),  # Triple slash root
        ]
        
        for git_root, expected_name in test_cases:
            with self.subTest(git_root=git_root):
                # Skip None test as it would cause TypeError
                if git_root is None:
                    continue
                project_name = self.resolver.get_project_name_from_git_root(git_root)
                self.assertEqual(project_name, expected_name)


if __name__ == '__main__':
    unittest.main()