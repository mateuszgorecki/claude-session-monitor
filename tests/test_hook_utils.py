#!/usr/bin/env python3
"""
Tests for hook_utils.py - Testing the new get_project_name_cached() function
"""
import unittest
import tempfile
import os
import sys
from unittest.mock import patch, Mock

# Add project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hooks.hook_utils import get_project_name_cached
from src.shared.project_name_resolver import ProjectNameResolver


class TestHookUtils(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'test_project_cache.json')
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_get_project_name_cached_uses_resolver(self):
        """Test that get_project_name_cached uses ProjectNameResolver"""
        test_path = '/test/project/path'
        expected_project_name = 'test-project'
        
        # Mock the resolver to return expected project name
        with patch('hooks.hook_utils.ProjectNameResolver') as mock_resolver_class:
            mock_resolver_instance = Mock()
            mock_resolver_instance.resolve_project_name.return_value = expected_project_name
            mock_resolver_class.return_value = mock_resolver_instance
            
            result = get_project_name_cached(test_path)
            
            # Verify resolver was called correctly
            mock_resolver_class.assert_called_once()
            mock_resolver_instance.resolve_project_name.assert_called_once_with(test_path)
            self.assertEqual(result, expected_project_name)
    
    def test_get_project_name_cached_with_default_path(self):
        """Test that get_project_name_cached uses current directory as default"""
        expected_project_name = 'current-project'
        
        with patch('hooks.hook_utils.ProjectNameResolver') as mock_resolver_class:
            mock_resolver_instance = Mock()
            mock_resolver_instance.resolve_project_name.return_value = expected_project_name
            mock_resolver_class.return_value = mock_resolver_instance
            
            with patch('os.getcwd', return_value='/current/directory'):
                result = get_project_name_cached()
                
                # Verify resolver was called with current directory
                mock_resolver_instance.resolve_project_name.assert_called_once_with('/current/directory')
                self.assertEqual(result, expected_project_name)
    
    def test_get_project_name_cached_uses_correct_cache_path(self):
        """Test that get_project_name_cached uses the correct cache file path"""
        with patch('hooks.hook_utils.get_project_cache_file_path') as mock_get_path:
            mock_get_path.return_value = self.cache_file
            
            with patch('hooks.hook_utils.ProjectNameResolver') as mock_resolver_class:
                mock_resolver_instance = Mock()
                mock_resolver_instance.resolve_project_name.return_value = 'test-project'
                mock_resolver_class.return_value = mock_resolver_instance
                
                get_project_name_cached('/test/path')
                
                # Verify cache file path was retrieved
                mock_get_path.assert_called_once()
                # Verify resolver was initialized with correct cache path
                mock_resolver_class.assert_called_once_with(self.cache_file)
    
    def test_get_project_name_cached_handles_resolver_errors(self):
        """Test that get_project_name_cached handles resolver errors gracefully"""
        with patch('hooks.hook_utils.ProjectNameResolver') as mock_resolver_class:
            mock_resolver_instance = Mock()
            mock_resolver_instance.resolve_project_name.side_effect = Exception("Resolver error")
            mock_resolver_class.return_value = mock_resolver_instance
            
            # Should fall back to basename of path
            result = get_project_name_cached('/test/fallback/path')
            self.assertEqual(result, 'path')
    
    def test_get_project_name_cached_handles_none_path(self):
        """Test that get_project_name_cached handles None path gracefully"""
        with patch('hooks.hook_utils.ProjectNameResolver') as mock_resolver_class:
            mock_resolver_instance = Mock()
            mock_resolver_instance.resolve_project_name.return_value = 'unknown'
            mock_resolver_class.return_value = mock_resolver_instance
            
            with patch('os.getcwd', return_value='/current/directory'):
                result = get_project_name_cached(None)
                
                # Should use current directory as fallback
                mock_resolver_instance.resolve_project_name.assert_called_with('/current/directory')
    
    def test_get_project_name_cached_handles_empty_path(self):
        """Test that get_project_name_cached handles empty path gracefully"""
        with patch('hooks.hook_utils.ProjectNameResolver') as mock_resolver_class:
            mock_resolver_instance = Mock()
            mock_resolver_instance.resolve_project_name.return_value = 'unknown'
            mock_resolver_class.return_value = mock_resolver_instance
            
            with patch('os.getcwd', return_value='/current/directory'):
                result = get_project_name_cached('')
                
                # Should use current directory as fallback
                mock_resolver_instance.resolve_project_name.assert_called_with('/current/directory')


if __name__ == '__main__':
    unittest.main()