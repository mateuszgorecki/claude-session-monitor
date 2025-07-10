#!/usr/bin/env python3
"""
Integration tests for hook refactoring with ProjectNameResolver.
Tests that all hooks work correctly with the new cached project name system.
"""
import unittest
import tempfile
import os
import json
import sys
from unittest.mock import patch, Mock
from io import StringIO

# Add project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the hook modules
from hooks.notification_hook import main as notification_main
from hooks.stop_hook import main as stop_main
from hooks.activity_hook import main as activity_main
from hooks.hook_utils import get_project_name_cached


class TestHookIntegration(unittest.TestCase):
    """Integration tests for hook refactoring with ProjectNameResolver."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'test_integration.log')
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_notification_hook_uses_cached_project_name(self):
        """Test that notification hook uses cached project name resolution."""
        # Mock input data
        notification_data = {
            "session_id": "test-session-123",
            "transcript_path": "/path/to/transcript.jsonl",
            "message": "Test notification",
            "title": "Test Title"
        }
        
        # Mock stdin input
        stdin_input = json.dumps(notification_data)
        
        # Mock get_project_name_cached to return known project name
        with patch('hooks.notification_hook.get_project_name_cached') as mock_get_project:
            mock_get_project.return_value = 'test-project'
            
            # Set environment variable for log file
            with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file}):
                # Mock stdin
                with patch('sys.stdin', StringIO(stdin_input)):
                    notification_main()
        
        # Verify log file was created and contains expected data
        self.assertTrue(os.path.exists(self.log_file))
        
        # Read and verify log content
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            log_entry = json.loads(log_content.strip())
            
            # Verify the hook used the mocked project name
            self.assertEqual(log_entry['project_name'], 'test-project')
            self.assertEqual(log_entry['event_type'], 'notification')
            self.assertEqual(log_entry['session_id'], 'test-session-123')
            
        # Verify the cached resolver was called
        mock_get_project.assert_called_once()
    
    def test_stop_hook_uses_cached_project_name(self):
        """Test that stop hook uses cached project name resolution."""
        # Mock input data
        stop_data = {
            "session_id": "test-session-456",
            "transcript_path": "/path/to/transcript.jsonl",
            "stop_hook_active": False
        }
        
        # Mock stdin input
        stdin_input = json.dumps(stop_data)
        
        # Mock get_project_name_cached to return known project name
        with patch('hooks.stop_hook.get_project_name_cached') as mock_get_project:
            mock_get_project.return_value = 'test-project-stop'
            
            # Set environment variable for log file
            with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file}):
                # Mock stdin
                with patch('sys.stdin', StringIO(stdin_input)):
                    stop_main()
        
        # Verify log file was created and contains expected data
        self.assertTrue(os.path.exists(self.log_file))
        
        # Read and verify log content
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            log_entry = json.loads(log_content.strip())
            
            # Verify the hook used the mocked project name
            self.assertEqual(log_entry['project_name'], 'test-project-stop')
            self.assertEqual(log_entry['event_type'], 'stop')
            self.assertEqual(log_entry['session_id'], 'test-session-456')
            
        # Verify the cached resolver was called
        mock_get_project.assert_called_once()
    
    def test_activity_hook_uses_cached_project_name(self):
        """Test that activity hook uses cached project name resolution."""
        # Mock input data
        activity_data = {
            "session_id": "test-session-789",
            "transcript_path": "/path/to/transcript.jsonl",
            "tool_name": "Bash",
            "parameters": {"command": "ls"}
        }
        
        # Mock stdin input
        stdin_input = json.dumps(activity_data)
        
        # Mock get_project_name_cached to return known project name
        with patch('hooks.activity_hook.get_project_name_cached') as mock_get_project:
            mock_get_project.return_value = 'test-project-activity'
            
            # Set environment variable for log file
            with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file}):
                # Mock stdin
                with patch('sys.stdin', StringIO(stdin_input)):
                    activity_main()
        
        # Verify log file was created and contains expected data
        self.assertTrue(os.path.exists(self.log_file))
        
        # Read and verify log content
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            log_entry = json.loads(log_content.strip())
            
            # Verify the hook used the mocked project name
            self.assertEqual(log_entry['project_name'], 'test-project-activity')
            self.assertEqual(log_entry['event_type'], 'activity')
            self.assertEqual(log_entry['session_id'], 'test-session-789')
            
        # Verify the cached resolver was called
        mock_get_project.assert_called_once()
    
    def test_all_hooks_use_consistent_project_name(self):
        """Test that all hooks use the same cached project name for the same working directory."""
        # Mock all hooks to use the same cached project name
        with patch('hooks.notification_hook.get_project_name_cached') as mock_get_project_notif, \
             patch('hooks.stop_hook.get_project_name_cached') as mock_get_project_stop, \
             patch('hooks.activity_hook.get_project_name_cached') as mock_get_project_activity:
            
            # Set all mocks to return the same project name
            mock_get_project_notif.return_value = 'consistent-project'
            mock_get_project_stop.return_value = 'consistent-project'
            mock_get_project_activity.return_value = 'consistent-project'
            
            # Test notification hook
            notification_data = {"session_id": "test-1", "message": "Test"}
            with patch('sys.stdin', StringIO(json.dumps(notification_data))):
                with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file + '_notification'}):
                    notification_main()
            
            # Test stop hook
            stop_data = {"session_id": "test-2", "stop_hook_active": False}
            with patch('sys.stdin', StringIO(json.dumps(stop_data))):
                with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file + '_stop'}):
                    stop_main()
            
            # Test activity hook
            activity_data = {"session_id": "test-3", "tool_name": "Bash"}
            with patch('sys.stdin', StringIO(json.dumps(activity_data))):
                with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file + '_activity'}):
                    activity_main()
            
            # Verify all hooks called the cached resolver
            mock_get_project_notif.assert_called_once()
            mock_get_project_stop.assert_called_once()
            mock_get_project_activity.assert_called_once()
            
            # Verify all hooks used the same project name
            for suffix in ['_notification', '_stop', '_activity']:
                log_file_path = self.log_file + suffix
                if os.path.exists(log_file_path):
                    with open(log_file_path, 'r') as f:
                        log_entry = json.loads(f.read().strip())
                        self.assertEqual(log_entry['project_name'], 'consistent-project')
    
    def test_hook_integration_with_real_project_resolver(self):
        """Test hooks work with real ProjectNameResolver (not mocked)."""
        # Create a temporary git repository for testing
        git_repo_dir = os.path.join(self.temp_dir, 'test-git-repo')
        os.makedirs(git_repo_dir)
        
        # Create temporary cache file for this test
        test_cache_file = os.path.join(self.temp_dir, 'test_cache.json')
        
        # Initialize git repo
        import subprocess
        try:
            subprocess.run(['git', 'init'], cwd=git_repo_dir, check=True, capture_output=True)
            
            # Test notification hook with real resolver but using temporary cache file
            notification_data = {"session_id": "real-test", "message": "Real test"}
            with patch('sys.stdin', StringIO(json.dumps(notification_data))):
                with patch.dict(os.environ, {'CLAUDE_ACTIVITY_LOG_FILE': self.log_file}):
                    with patch('os.getcwd', return_value=git_repo_dir):
                        # CRITICAL: Mock cache file path to use temporary file, not production!
                        with patch('hooks.hook_utils.get_project_cache_file_path', return_value=test_cache_file):
                            notification_main()
            
            # Verify log file was created
            self.assertTrue(os.path.exists(self.log_file))
            
            # Read and verify log content
            with open(self.log_file, 'r') as f:
                log_entry = json.loads(f.read().strip())
                
                # Project name should be the git repository directory name
                self.assertEqual(log_entry['project_name'], 'test-git-repo')
                self.assertEqual(log_entry['event_type'], 'notification')
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Skip test if git is not available
            self.skipTest("Git command not available for integration test")


if __name__ == '__main__':
    unittest.main()