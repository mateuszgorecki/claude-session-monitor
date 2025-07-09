#!/usr/bin/env python3
"""
Tests for project name caching system data models.
"""
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import os
import sys
import tempfile
import json
import threading
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.project_models import ProjectInfo, ProjectCache


class TestProjectInfo(unittest.TestCase):
    """Test ProjectInfo data model."""
    
    def test_create_project_info_with_git_root_and_empty_aliases(self):
        """Test creating ProjectInfo with git_root and empty aliases list."""
        # Arrange
        git_root = "/path/to/project"
        expected_project_name = "project"
        
        # Act
        project_info = ProjectInfo(git_root=git_root)
        
        # Assert
        self.assertEqual(project_info.git_root, git_root)
        self.assertEqual(project_info.project_name, expected_project_name)
        self.assertEqual(project_info.aliases, [])
        self.assertIsInstance(project_info.last_accessed, datetime)
        self.assertTrue(project_info.last_accessed.tzinfo is not None)  # Should be timezone-aware
    
    def test_add_alias_method(self):
        """Test adding an alias to ProjectInfo."""
        # Arrange
        git_root = "/path/to/project"
        alias_path = "/path/to/project/subdir"
        project_info = ProjectInfo(git_root=git_root)
        initial_accessed_time = project_info.last_accessed
        
        # Add small delay to ensure timestamp difference
        time.sleep(0.001)
        
        # Act
        project_info.add_alias(alias_path)
        
        # Assert
        self.assertEqual(len(project_info.aliases), 1)
        self.assertIn(alias_path, project_info.aliases)
        self.assertTrue(project_info.last_accessed > initial_accessed_time)
    
    def test_add_duplicate_alias_ignored(self):
        """Test that adding the same alias twice doesn't create duplicates."""
        # Arrange
        git_root = "/path/to/project"
        alias_path = "/path/to/project/subdir"
        project_info = ProjectInfo(git_root=git_root)
        
        # Act
        project_info.add_alias(alias_path)
        project_info.add_alias(alias_path)  # Add same alias again
        
        # Assert
        self.assertEqual(len(project_info.aliases), 1)
        self.assertIn(alias_path, project_info.aliases)


class TestProjectCache(unittest.TestCase):
    """Test ProjectCache class."""
    
    def test_load_with_nonexistent_file(self):
        """Test loading cache from non-existent file returns empty dict."""
        # Arrange
        cache_file = "/tmp/nonexistent_cache.json"
        cache = ProjectCache(cache_file)
        
        # Act
        result = cache.load()
        
        # Assert
        self.assertEqual(result, {})
        self.assertIsInstance(result, dict)
    
    def test_save_and_load_roundtrip(self):
        """Test saving and loading project data."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            cache_file = f.name
        
        try:
            cache = ProjectCache(cache_file)
            project_info = ProjectInfo("/path/to/project")
            project_info.add_alias("/path/to/project/subdir")
            data = {"project": project_info}
            
            # Act
            cache.save(data)
            loaded_data = cache.load()
            
            # Assert
            self.assertEqual(len(loaded_data), 1)
            self.assertIn("project", loaded_data)
            loaded_project = loaded_data["project"]
            self.assertEqual(loaded_project.git_root, "/path/to/project")
            self.assertEqual(loaded_project.project_name, "project")
            self.assertEqual(loaded_project.aliases, ["/path/to/project/subdir"])
            
        finally:
            os.unlink(cache_file)
    
    def test_find_project_by_alias(self):
        """Test finding project by alias path."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            cache_file = f.name
        
        try:
            cache = ProjectCache(cache_file)
            project_info = ProjectInfo("/path/to/project")
            project_info.add_alias("/path/to/project/subdir")
            data = {"project": project_info}
            cache.save(data)
            
            # Act
            found_project = cache.find_project_by_alias("/path/to/project/subdir")
            not_found_project = cache.find_project_by_alias("/nonexistent/path")
            
            # Assert
            self.assertEqual(found_project, "project")
            self.assertIsNone(not_found_project)
            
        finally:
            os.unlink(cache_file)
    
    def test_add_alias(self):
        """Test adding alias to existing project."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            cache_file = f.name
        
        try:
            cache = ProjectCache(cache_file)
            project_info = ProjectInfo("/path/to/project")
            data = {"project": project_info}
            cache.save(data)
            
            # Act
            cache.add_alias("project", "/path/to/project/new_subdir")
            
            # Assert
            loaded_data = cache.load()
            loaded_project = loaded_data["project"]
            self.assertIn("/path/to/project/new_subdir", loaded_project.aliases)
            
        finally:
            os.unlink(cache_file)
    
    def test_concurrent_save_operations(self):
        """Test concurrent save operations for thread safety."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            cache_file = f.name
        
        try:
            cache = ProjectCache(cache_file)
            results = []
            errors = []
            
            def save_operation(thread_id):
                """Save operation to run in separate thread."""
                try:
                    project_info = ProjectInfo(f"/path/to/project{thread_id}")
                    project_info.add_alias(f"/path/to/project{thread_id}/subdir")
                    data = {f"project{thread_id}": project_info}
                    cache.save(data)
                    results.append(f"success_{thread_id}")
                except Exception as e:
                    errors.append(f"error_{thread_id}: {str(e)}")
            
            # Act - run multiple save operations concurrently
            threads = []
            for i in range(5):
                thread = threading.Thread(target=save_operation, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Assert - all operations should succeed without corruption
            self.assertEqual(len(errors), 0, f"Concurrent operations failed: {errors}")
            self.assertEqual(len(results), 5, f"Expected 5 successful operations, got {len(results)}")
            
            # Verify file is not corrupted by loading it
            loaded_data = cache.load()
            self.assertIsInstance(loaded_data, dict)
            
        finally:
            os.unlink(cache_file)


if __name__ == '__main__':
    unittest.main()