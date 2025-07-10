#!/usr/bin/env python3
"""
Tests for ProjectNameResolver class - core project name resolution logic.
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.project_name_resolver import ProjectNameResolver
from src.shared.project_models import ProjectInfo, ProjectCache
from src.shared.git_resolver import GitResolver


class TestProjectNameResolver(unittest.TestCase):
    """Test ProjectNameResolver class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary cache file for testing
        self.temp_cache_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_cache_file.close()
        self.cache_file_path = self.temp_cache_file.name
        
        self.resolver = ProjectNameResolver(self.cache_file_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.cache_file_path)
        except FileNotFoundError:
            pass
    
    def test_resolve_project_name_cache_hit_direct_path(self):
        """Test resolve_project_name() returns cached result for direct path match."""
        # Arrange - populate cache with project
        project_info = ProjectInfo("/path/to/project")
        cache_data = {"project": project_info}
        cache = ProjectCache(self.cache_file_path)
        cache.save(cache_data)
        
        # Act
        result = self.resolver.resolve_project_name("/path/to/project")
        
        # Assert
        self.assertEqual(result, "project")
    
    def test_resolve_project_name_cache_hit_alias_path(self):
        """Test resolve_project_name() returns cached result for alias path match."""
        # Arrange - populate cache with project that has alias
        project_info = ProjectInfo("/path/to/project")
        project_info.add_alias("/path/to/project/subdir")
        cache_data = {"project": project_info}
        cache = ProjectCache(self.cache_file_path)
        cache.save(cache_data)
        
        # Act
        result = self.resolver.resolve_project_name("/path/to/project/subdir")
        
        # Assert
        self.assertEqual(result, "project")
    
    def test_resolve_project_name_cache_miss_git_detection(self):
        """Test resolve_project_name() handles cache miss with git detection."""
        # Arrange - empty cache, mock git resolver
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root, \
             patch.object(self.resolver.git_resolver, 'get_project_name_from_git_root') as mock_project_name:
            
            mock_git_root.return_value = "/path/to/project"
            mock_project_name.return_value = "project"
            
            # Act
            result = self.resolver.resolve_project_name("/path/to/project/subdir")
            
            # Assert
            self.assertEqual(result, "project")
            mock_git_root.assert_called_once_with("/path/to/project/subdir")
            mock_project_name.assert_called_once_with("/path/to/project")
    
    def test_resolve_project_name_cache_miss_git_failure_fallback(self):
        """Test resolve_project_name() falls back to basename when git fails."""
        # Arrange - empty cache, mock git resolver to fail
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root:
            mock_git_root.return_value = None  # Git detection fails
            
            # Act
            result = self.resolver.resolve_project_name("/path/to/some/directory")
            
            # Assert
            self.assertEqual(result, "directory")  # basename of path
            mock_git_root.assert_called_once_with("/path/to/some/directory")
    
    def test_resolve_project_name_updates_cache_on_git_success(self):
        """Test resolve_project_name() updates cache when git detection succeeds."""
        # Arrange - empty cache, mock git resolver
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root, \
             patch.object(self.resolver.git_resolver, 'get_project_name_from_git_root') as mock_project_name:
            
            mock_git_root.return_value = "/path/to/project"
            mock_project_name.return_value = "project"
            
            # Act
            result = self.resolver.resolve_project_name("/path/to/project/subdir")
            
            # Assert
            self.assertEqual(result, "project")
            
            # Verify cache was updated
            cache = ProjectCache(self.cache_file_path)
            cache_data = cache.load()
            self.assertIn("project", cache_data)
            self.assertEqual(cache_data["project"].git_root, "/path/to/project")
            self.assertIn("/path/to/project/subdir", cache_data["project"].aliases)
    
    def test_resolve_project_name_creates_alias_for_subdirectory(self):
        """Test resolve_project_name() creates alias when path is subdirectory of git root."""
        # Arrange - empty cache, mock git resolver
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root, \
             patch.object(self.resolver.git_resolver, 'get_project_name_from_git_root') as mock_project_name:
            
            mock_git_root.return_value = "/path/to/project"
            mock_project_name.return_value = "project"
            
            # Act
            result = self.resolver.resolve_project_name("/path/to/project/deep/subdir")
            
            # Assert
            self.assertEqual(result, "project")
            
            # Verify alias was created
            cache = ProjectCache(self.cache_file_path)
            cache_data = cache.load()
            self.assertIn("/path/to/project/deep/subdir", cache_data["project"].aliases)
    
    def test_resolve_project_name_handles_git_root_exactly(self):
        """Test resolve_project_name() handles git root path exactly without creating alias."""
        # Arrange - empty cache, mock git resolver
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root, \
             patch.object(self.resolver.git_resolver, 'get_project_name_from_git_root') as mock_project_name:
            
            mock_git_root.return_value = "/path/to/project"
            mock_project_name.return_value = "project"
            
            # Act
            result = self.resolver.resolve_project_name("/path/to/project")
            
            # Assert
            self.assertEqual(result, "project")
            
            # Verify no alias was created (since it's the git root itself)
            cache = ProjectCache(self.cache_file_path)
            cache_data = cache.load()
            self.assertEqual(cache_data["project"].aliases, [])


    def test_resolve_project_name_multiple_projects_in_cache(self):
        """Test resolve_project_name() handles multiple projects in cache correctly."""
        # Arrange - populate cache with multiple projects
        project1 = ProjectInfo("/path/to/project1")
        project1.add_alias("/path/to/project1/subdir")
        project2 = ProjectInfo("/path/to/project2")
        project2.add_alias("/path/to/project2/subdir")
        
        cache_data = {"project1": project1, "project2": project2}
        cache = ProjectCache(self.cache_file_path)
        cache.save(cache_data)
        
        # Act & Assert
        self.assertEqual(self.resolver.resolve_project_name("/path/to/project1/subdir"), "project1")
        self.assertEqual(self.resolver.resolve_project_name("/path/to/project2/subdir"), "project2")
        self.assertEqual(self.resolver.resolve_project_name("/path/to/project1"), "project1")
        self.assertEqual(self.resolver.resolve_project_name("/path/to/project2"), "project2")
    
    def test_resolve_project_name_empty_path_fallback(self):
        """Test resolve_project_name() handles empty path gracefully."""
        # Act
        result = self.resolver.resolve_project_name("")
        
        # Assert
        self.assertEqual(result, "unknown")
    
    def test_resolve_project_name_none_path_fallback(self):
        """Test resolve_project_name() handles None path gracefully."""
        # Act
        result = self.resolver.resolve_project_name(None)
        
        # Assert
        self.assertEqual(result, "unknown")
    
    def test_resolve_project_name_cache_file_errors(self):
        """Test resolve_project_name() handles cache file errors gracefully."""
        # Arrange - create resolver with non-writable cache path
        readonly_cache_path = "/read-only-path/cache.json"
        resolver = ProjectNameResolver(readonly_cache_path)
        
        with patch.object(resolver.git_resolver, 'get_git_root') as mock_git_root:
            mock_git_root.return_value = None  # Force fallback
            
            # Act - should not crash despite cache errors
            result = resolver.resolve_project_name("/some/path")
            
            # Assert
            self.assertEqual(result, "path")
    
    def test_resolve_project_name_adaptive_learning_deep_subdirectory(self):
        """Test resolve_project_name() learns from deep subdirectory navigation."""
        # Arrange - mock git resolver for deep subdirectory
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root, \
             patch.object(self.resolver.git_resolver, 'get_project_name_from_git_root') as mock_project_name:
            
            mock_git_root.return_value = "/path/to/project"
            mock_project_name.return_value = "project"
            
            # Act - first call creates cache entry with deep alias
            result1 = self.resolver.resolve_project_name("/path/to/project/src/components/deep")
            
            # Second call to different subdirectory should add another alias
            result2 = self.resolver.resolve_project_name("/path/to/project/docs/api")
            
            # Assert
            self.assertEqual(result1, "project")
            self.assertEqual(result2, "project")
            
            # Verify both aliases were created
            cache = ProjectCache(self.cache_file_path)
            cache_data = cache.load()
            aliases = cache_data["project"].aliases
            self.assertIn("/path/to/project/src/components/deep", aliases)
            self.assertIn("/path/to/project/docs/api", aliases)
    
    def test_resolve_project_name_concurrent_access_simulation(self):
        """Test resolve_project_name() handles concurrent-like access patterns."""
        # Arrange - mock git resolver
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root, \
             patch.object(self.resolver.git_resolver, 'get_project_name_from_git_root') as mock_project_name:
            
            mock_git_root.return_value = "/path/to/project"
            mock_project_name.return_value = "project"
            
            # Act - simulate multiple rapid calls (as might happen in concurrent hook calls)
            paths = [
                "/path/to/project",
                "/path/to/project/src",
                "/path/to/project/tests",
                "/path/to/project/docs",
                "/path/to/project/src/components"
            ]
            
            results = []
            for path in paths:
                result = self.resolver.resolve_project_name(path)
                results.append(result)
            
            # Assert - all should return same project name
            self.assertEqual(set(results), {"project"})
            
            # Verify cache consistency
            cache = ProjectCache(self.cache_file_path)
            cache_data = cache.load()
            self.assertEqual(len(cache_data), 1)
            self.assertIn("project", cache_data)
    
    def test_resolve_project_name_git_timeout_fallback(self):
        """Test resolve_project_name() handles git timeout gracefully."""
        # Arrange - mock git resolver to simulate timeout
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root:
            mock_git_root.return_value = None  # Simulate timeout/failure
            
            # Act
            result = self.resolver.resolve_project_name("/path/to/some/project")
            
            # Assert - should fall back to basename
            self.assertEqual(result, "project")
    
    def test_resolve_project_name_cache_corruption_recovery(self):
        """Test resolve_project_name() recovers from cache corruption."""
        # Arrange - create corrupted cache file
        with open(self.cache_file_path, 'w') as f:
            f.write("invalid json content")
        
        with patch.object(self.resolver.git_resolver, 'get_git_root') as mock_git_root, \
             patch.object(self.resolver.git_resolver, 'get_project_name_from_git_root') as mock_project_name:
            
            mock_git_root.return_value = "/path/to/project"
            mock_project_name.return_value = "project"
            
            # Act - should recover from corruption and work normally
            result = self.resolver.resolve_project_name("/path/to/project")
            
            # Assert
            self.assertEqual(result, "project")
            
            # Verify cache is now valid
            cache = ProjectCache(self.cache_file_path)
            cache_data = cache.load()
            self.assertIn("project", cache_data)


if __name__ == '__main__':
    unittest.main()