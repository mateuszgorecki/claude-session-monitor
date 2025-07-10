#!/usr/bin/env python3
"""
Tests for memory management and cache cleanup in project name caching system.
"""
import unittest
import tempfile
import os
import sys
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.project_models import ProjectCache, ProjectInfo
from shared.memory_manager import MemoryManager
from shared.project_name_resolver import ProjectNameResolver


class TestMemoryManager(unittest.TestCase):
    """Test cases for MemoryManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'test_cache.json')
        self.cache = ProjectCache(self.cache_file)
        self.memory_manager = MemoryManager(self.cache, max_entries=5)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initial_state(self):
        """Test memory manager initial state."""
        self.assertEqual(self.memory_manager.get_cache_size(), 0)
        self.assertEqual(self.memory_manager.get_max_entries(), 5)
        self.assertFalse(self.memory_manager.needs_cleanup())
    
    def test_cache_size_tracking(self):
        """Test cache size tracking."""
        # Add some entries
        cache_data = {
            'project1': ProjectInfo('/path/to/project1'),
            'project2': ProjectInfo('/path/to/project2'),
            'project3': ProjectInfo('/path/to/project3')
        }
        self.cache.save(cache_data)
        
        # Check size tracking
        self.assertEqual(self.memory_manager.get_cache_size(), 3)
    
    def test_needs_cleanup_detection(self):
        """Test cleanup need detection."""
        # Fill cache beyond limit
        cache_data = {}
        for i in range(7):  # More than max_entries (5)
            cache_data[f'project{i}'] = ProjectInfo(f'/path/to/project{i}')
        
        self.cache.save(cache_data)
        
        # Should detect need for cleanup
        self.assertTrue(self.memory_manager.needs_cleanup())
        self.assertEqual(self.memory_manager.get_cache_size(), 7)
    
    def test_lru_cleanup_strategy(self):
        """Test LRU (Least Recently Used) cleanup strategy."""
        # Create projects with different access times
        cache_data = {}
        from datetime import datetime, timezone
        base_time = datetime.now(timezone.utc)
        
        for i in range(7):
            project_info = ProjectInfo(f'/path/to/project{i}')
            # Set different last_accessed times (older first)
            # project0 is oldest, project6 is newest
            hours_ago = (7-i) 
            project_info.last_accessed = base_time.replace(
                hour=max(0, base_time.hour - hours_ago)
            )
            cache_data[f'project{i}'] = project_info
        
        self.cache.save(cache_data)
        
        # Perform cleanup
        cleaned_data = self.memory_manager.cleanup_cache()
        
        # Should keep only 5 most recently used entries
        self.assertEqual(len(cleaned_data), 5)
        
        # Should keep projects 2, 3, 4, 5, 6 (most recent)
        remaining_projects = set(cleaned_data.keys())
        expected_projects = {'project2', 'project3', 'project4', 'project5', 'project6'}
        self.assertEqual(remaining_projects, expected_projects)
    
    def test_cleanup_preserves_aliases(self):
        """Test that cleanup preserves project aliases."""
        # Create project with aliases
        project_info = ProjectInfo('/path/to/main')
        project_info.add_alias('/path/to/main/sub1')
        project_info.add_alias('/path/to/main/sub2')
        
        cache_data = {'main_project': project_info}
        
        # Add more projects to trigger cleanup
        for i in range(6):
            cache_data[f'project{i}'] = ProjectInfo(f'/path/to/project{i}')
        
        self.cache.save(cache_data)
        
        # Perform cleanup
        cleaned_data = self.memory_manager.cleanup_cache()
        
        # Verify aliases are preserved for remaining projects
        for project_name, project_info in cleaned_data.items():
            if project_name == 'main_project':
                self.assertIn('/path/to/main/sub1', project_info.aliases)
                self.assertIn('/path/to/main/sub2', project_info.aliases)
    
    def test_get_cleanup_summary(self):
        """Test cleanup summary generation."""
        # Fill cache beyond limit
        cache_data = {}
        for i in range(7):
            cache_data[f'project{i}'] = ProjectInfo(f'/path/to/project{i}')
        
        self.cache.save(cache_data)
        
        # Get summary before cleanup
        summary = self.memory_manager.get_cleanup_summary()
        
        self.assertIn('7 entries', summary)
        self.assertIn('limit: 5', summary)
        self.assertIn('cleanup needed', summary)


class TestProjectNameResolverWithMemoryManagement(unittest.TestCase):
    """Test ProjectNameResolver integration with memory management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'test_cache.json')
        self.resolver = ProjectNameResolver(self.cache_file, max_cache_entries=3)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_resolver_has_memory_manager(self):
        """Test that resolver has memory management capabilities."""
        self.assertIsNotNone(self.resolver.get_memory_manager())
        self.assertIsInstance(self.resolver.get_memory_manager(), MemoryManager)
    
    def test_automatic_cleanup_on_limit(self):
        """Test automatic cleanup when cache limit is exceeded."""
        # Add entries beyond limit
        test_paths = ['/test/project1', '/test/project2', '/test/project3', '/test/project4']
        
        for path in test_paths:
            self.resolver.resolve_project_name(path)
        
        # Check that cache was automatically cleaned up
        memory_manager = self.resolver.get_memory_manager()
        self.assertLessEqual(memory_manager.get_cache_size(), 3)
    
    def test_manual_cache_cleanup(self):
        """Test manual cache cleanup through resolver."""
        # Temporarily disable automatic cleanup by directly adding to cache
        cache_data = {}
        for i in range(5):
            cache_data[f'project{i}'] = ProjectInfo(f'/test/project{i}')
        
        # Save directly to bypass automatic cleanup
        self.resolver.cache.save(cache_data)
        
        # Verify cache is over limit
        memory_manager = self.resolver.get_memory_manager()
        self.assertGreater(memory_manager.get_cache_size(), 3)
        
        # Manual cleanup
        cleanup_summary = self.resolver.cleanup_cache()
        
        # Verify cleanup occurred
        self.assertIsInstance(cleanup_summary, str)
        self.assertTrue(
            'removed' in cleanup_summary.lower() or 'no action needed' in cleanup_summary.lower()
        )
        
        self.assertLessEqual(memory_manager.get_cache_size(), 3)
    
    def test_cache_size_monitoring(self):
        """Test cache size monitoring capabilities."""
        # Add some entries
        for i in range(3):
            self.resolver.resolve_project_name(f'/test/project{i}')
        
        # Check size monitoring
        memory_manager = self.resolver.get_memory_manager()
        self.assertEqual(memory_manager.get_cache_size(), 3)
        self.assertEqual(memory_manager.get_max_entries(), 3)


if __name__ == '__main__':
    unittest.main()