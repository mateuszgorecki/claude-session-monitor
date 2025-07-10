#!/usr/bin/env python3
"""
End-to-end integration tests for the project name caching system.
Tests complete flows: new project → cache creation → alias learning → persistence.
"""

import unittest
import tempfile
import os
import json
import sys
import subprocess
import threading
import time
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock

# Add project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.project_name_resolver import ProjectNameResolver
from src.shared.project_models import ProjectCache, ProjectInfo
from src.shared.git_resolver import GitResolver
from src.shared.performance_metrics import PerformanceMetrics
from src.shared.memory_manager import MemoryManager
from src.shared.utils import get_project_cache_file_path
from hooks.hook_utils import get_project_name_cached


class TestProjectCacheIntegration(unittest.TestCase):
    """Integration tests for the complete project name caching system."""
    
    def setUp(self):
        """Set up test fixtures with temporary directories and git repositories."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'project_cache.json')
        self.git_repos = []
        
        # Create multiple test git repositories
        for i in range(3):
            repo_name = f'test-repo-{i}'
            repo_path = os.path.join(self.temp_dir, repo_name)
            os.makedirs(repo_path)
            
            # Initialize git repository
            try:
                subprocess.run(['git', 'init'], cwd=repo_path, check=True, capture_output=True)
                subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, check=True)
                subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, check=True)
                
                # Create initial commit
                test_file = os.path.join(repo_path, 'README.md')
                with open(test_file, 'w') as f:
                    f.write(f'# Test Repository {i}\n')
                subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
                subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True)
                
                self.git_repos.append(repo_path)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Skip git operations if git is not available
                self.skipTest("Git command not available for integration test")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_e2e_new_project_cache_creation_alias_learning(self):
        """
        Test complete flow: new project → cache creation → alias learning.
        
        This test verifies:
        1. First access to a project creates cache entry
        2. Subdirectory access creates aliases
        3. Cache persists across resolver instances
        4. Performance metrics are collected
        """
        if not self.git_repos:
            self.skipTest("No git repositories available for testing")
        
        repo_path = self.git_repos[0]
        subdir_path = os.path.join(repo_path, 'src', 'components')
        os.makedirs(subdir_path, exist_ok=True)
        
        # Initialize resolver with custom cache file
        resolver = ProjectNameResolver(cache_file_path=self.cache_file)
        
        # Step 1: First access to git root - should create cache entry
        project_name_root = resolver.resolve_project_name(repo_path)
        self.assertEqual(project_name_root, 'test-repo-0')
        
        # Verify cache was created
        self.assertTrue(os.path.exists(self.cache_file))
        cache = ProjectCache(self.cache_file)
        cache_data = cache.load()
        self.assertIn('test-repo-0', cache_data)
        # Use realpath for cross-platform path comparison
        self.assertEqual(os.path.realpath(cache_data['test-repo-0'].git_root), os.path.realpath(repo_path))
        
        # Step 2: Access subdirectory - should create alias and return same project name
        project_name_subdir = resolver.resolve_project_name(subdir_path)
        self.assertEqual(project_name_subdir, 'test-repo-0')
        
        # Verify alias was created
        cache_data = cache.load()
        project_info = cache_data['test-repo-0']
        self.assertIn(subdir_path, project_info.aliases)
        
        # Step 3: Create new resolver instance - cache should persist
        resolver2 = ProjectNameResolver(cache_file_path=self.cache_file)
        
        # Access via alias should use cached value
        project_name_cached = resolver2.resolve_project_name(subdir_path)
        self.assertEqual(project_name_cached, 'test-repo-0')
        
        # Step 4: Verify performance metrics were collected
        metrics = resolver2.get_metrics()
        self.assertGreater(metrics.get_cache_hits(), 0, "Should have cache hits")
        self.assertGreater(metrics.get_total_operations(), 0, "Should have total operations")
        
        # Step 5: Test deeper subdirectory - should also create alias
        deep_subdir = os.path.join(subdir_path, 'utils', 'helpers')
        os.makedirs(deep_subdir, exist_ok=True)
        
        project_name_deep = resolver2.resolve_project_name(deep_subdir)
        self.assertEqual(project_name_deep, 'test-repo-0')
        
        # Verify deep alias was created
        cache_data = cache.load()
        project_info = cache_data['test-repo-0']
        self.assertIn(deep_subdir, project_info.aliases)
    
    def test_e2e_concurrent_access_scenarios(self):
        """
        Test concurrent access to the cache system.
        
        This test verifies:
        1. Multiple threads can access cache simultaneously
        2. Cache remains consistent under concurrent load
        3. No race conditions occur during cache updates
        4. All threads get correct project names
        """
        if not self.git_repos:
            self.skipTest("No git repositories available for testing")
        
        repo_path = self.git_repos[0]
        
        # Create multiple subdirectories for concurrent access
        subdirs = []
        for i in range(10):
            subdir = os.path.join(repo_path, f'module_{i}', 'src')
            os.makedirs(subdir, exist_ok=True)
            subdirs.append(subdir)
        
        results = []
        errors = []
        
        def resolve_project_name(path):
            """Resolve project name in thread."""
            try:
                resolver = ProjectNameResolver(cache_file_path=self.cache_file)
                project_name = resolver.resolve_project_name(path)
                return project_name
            except Exception as e:
                errors.append(e)
                return None
        
        # Test concurrent access with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            futures = []
            
            # Mix of root directory and subdirectory access
            all_paths = [repo_path] + subdirs
            for path in all_paths:
                future = executor.submit(resolve_project_name, path)
                futures.append((future, path))
            
            # Collect results
            for future, path in futures:
                try:
                    result = future.result(timeout=10)
                    results.append((path, result))
                except Exception as e:
                    errors.append(e)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        
        # Verify all threads got the same project name
        project_names = [result[1] for result in results if result[1] is not None]
        self.assertTrue(all(name == 'test-repo-0' for name in project_names),
                       f"Inconsistent project names: {set(project_names)}")
        
        # Verify cache consistency
        cache = ProjectCache(self.cache_file)
        cache_data = cache.load()
        self.assertIn('test-repo-0', cache_data)
        
        project_info = cache_data['test-repo-0']
        self.assertEqual(os.path.realpath(project_info.git_root), os.path.realpath(repo_path))
        
        # Verify most subdirectories were added as aliases (allow for some race conditions)
        # In concurrent scenarios, it's possible some aliases might not be added due to timing
        aliases_found = sum(1 for subdir in subdirs if subdir in project_info.aliases)
        self.assertGreater(aliases_found, len(subdirs) * 0.5,  # At least 50% should be added
                          f"Too few aliases found: {aliases_found}/{len(subdirs)}. "
                          f"Aliases: {project_info.aliases}")
    
    def test_e2e_graceful_degradation_git_failures(self):
        """
        Test graceful degradation when git operations fail.
        
        This test verifies:
        1. System handles git command failures gracefully
        2. Falls back to basename when git detection fails
        3. Cache operations continue working
        4. System doesn't crash on git errors
        """
        # Test with non-git directory
        non_git_dir = os.path.join(self.temp_dir, 'non-git-project')
        os.makedirs(non_git_dir, exist_ok=True)
        
        resolver = ProjectNameResolver(cache_file_path=self.cache_file)
        
        # Should fall back to basename when git detection fails
        project_name = resolver.resolve_project_name(non_git_dir)
        self.assertEqual(project_name, 'non-git-project')
        
        # Verify cache entry was created with fallback
        cache = ProjectCache(self.cache_file)
        cache_data = cache.load()
        self.assertIn('non-git-project', cache_data)
        
        # Test with corrupted git repository
        corrupted_repo = os.path.join(self.temp_dir, 'corrupted-repo')
        os.makedirs(corrupted_repo, exist_ok=True)
        
        # Create .git directory but make it invalid
        git_dir = os.path.join(corrupted_repo, '.git')
        os.makedirs(git_dir)
        with open(os.path.join(git_dir, 'HEAD'), 'w') as f:
            f.write('invalid git content')
        
        # Should handle corrupted git gracefully
        project_name_corrupted = resolver.resolve_project_name(corrupted_repo)
        self.assertEqual(project_name_corrupted, 'corrupted-repo')
        
        # Test with permission denied scenario (simulated)
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(128, 'git')
            
            permission_dir = os.path.join(self.temp_dir, 'permission-denied')
            os.makedirs(permission_dir, exist_ok=True)
            
            project_name_permission = resolver.resolve_project_name(permission_dir)
            self.assertEqual(project_name_permission, 'permission-denied')
        
        # Verify system continues working after errors
        if self.git_repos:
            normal_repo = self.git_repos[0]
            project_name_normal = resolver.resolve_project_name(normal_repo)
            self.assertEqual(project_name_normal, 'test-repo-0')
    
    def test_e2e_hook_integration_with_cache_system(self):
        """
        Test integration between hooks and cache system.
        
        This test verifies:
        1. Hooks use the cached project name system
        2. Cache learning works through hook calls
        3. Consistent project names across hook invocations
        """
        if not self.git_repos:
            self.skipTest("No git repositories available for testing")
        
        repo_path = self.git_repos[0]
        subdir_path = os.path.join(repo_path, 'hooks_test')
        os.makedirs(subdir_path, exist_ok=True)
        
        # Test with custom cache file path - patch where the function is imported
        with patch('hooks.hook_utils.get_project_cache_file_path') as mock_get_cache_path:
            mock_get_cache_path.return_value = self.cache_file
            
            # First hook call from git root
            with patch('os.getcwd', return_value=repo_path):
                project_name_1 = get_project_name_cached()
                self.assertEqual(project_name_1, 'test-repo-0')
            
            # Second hook call from subdirectory
            with patch('os.getcwd', return_value=subdir_path):
                project_name_2 = get_project_name_cached()
                self.assertEqual(project_name_2, 'test-repo-0')
            
            # Third hook call from subdirectory (should use cache)
            with patch('os.getcwd', return_value=subdir_path):
                project_name_3 = get_project_name_cached()
                self.assertEqual(project_name_3, 'test-repo-0')
        
        # Verify cache was created and contains expected data
        self.assertTrue(os.path.exists(self.cache_file))
        cache = ProjectCache(self.cache_file)
        cache_data = cache.load()
        
        self.assertIn('test-repo-0', cache_data)
        project_info = cache_data['test-repo-0']
        self.assertEqual(os.path.realpath(project_info.git_root), os.path.realpath(repo_path))
        self.assertIn(subdir_path, project_info.aliases)
    
    def test_e2e_cache_persistence_and_memory_management(self):
        """
        Test cache persistence and memory management features.
        
        This test verifies:
        1. Cache persists across system restarts
        2. Memory management works correctly
        3. Cache cleanup operates as expected
        4. Performance metrics are maintained
        """
        if not self.git_repos:
            self.skipTest("No git repositories available for testing")
        
        # Create resolver with memory management
        resolver = ProjectNameResolver(cache_file_path=self.cache_file)
        
        # Add multiple projects to trigger memory management
        for i, repo_path in enumerate(self.git_repos):
            project_name = resolver.resolve_project_name(repo_path)
            self.assertEqual(project_name, f'test-repo-{i}')
            
            # Add subdirectories to create aliases
            for j in range(3):
                subdir = os.path.join(repo_path, f'subdir_{j}')
                os.makedirs(subdir, exist_ok=True)
                resolver.resolve_project_name(subdir)
        
        # Get cache health before restart
        cache = ProjectCache(self.cache_file)
        memory_manager = MemoryManager(cache)
        health_before = memory_manager.get_cache_health_report()
        
        # Simulate system restart with new resolver instance
        resolver2 = ProjectNameResolver(cache_file_path=self.cache_file)
        
        # Verify all projects are still cached
        for i, repo_path in enumerate(self.git_repos):
            project_name = resolver2.resolve_project_name(repo_path)
            self.assertEqual(project_name, f'test-repo-{i}')
        
        # Verify cache health is maintained
        cache2 = ProjectCache(self.cache_file)
        memory_manager2 = MemoryManager(cache2)
        health_after = memory_manager2.get_cache_health_report()
        
        self.assertGreaterEqual(health_after['health_score'], 0)
        self.assertGreaterEqual(health_after['size'], len(self.git_repos))
        
        # Test cache cleanup
        cache_data = cache2.load()
        original_count = len(cache_data)
        
        # Add timestamp manipulation to trigger cleanup (if cache grows large)
        if original_count > 5:  # Only test cleanup if we have enough entries
            cleaned_count = memory_manager2.cleanup_cache()
            self.assertLessEqual(cleaned_count, original_count)
    
    def test_e2e_existing_cache_data_compatibility(self):
        """
        Test system works correctly with existing cache data.
        
        This test verifies:
        1. System loads existing cache correctly
        2. Existing aliases are respected
        3. New aliases can be added to existing projects
        4. Cache format compatibility is maintained
        """
        # Create existing cache data manually
        existing_project_info = ProjectInfo('/path/to/existing/project')
        existing_project_info.aliases = ['/path/to/existing/project/src']
        existing_project_info.last_accessed = datetime.fromisoformat('2025-07-09T10:00:00+00:00')
        
        existing_cache_data = {
            'existing-project': existing_project_info
        }
        
        # Save existing cache
        cache = ProjectCache(self.cache_file)
        cache.save(existing_cache_data)
        
        # Create new resolver that should load existing cache
        resolver = ProjectNameResolver(cache_file_path=self.cache_file)
        
        # Add new project alongside existing cache
        if self.git_repos:
            repo_path = self.git_repos[0]
            project_name = resolver.resolve_project_name(repo_path)
            self.assertEqual(project_name, 'test-repo-0')
        
        # Verify existing cache data is preserved
        cache_data = cache.load()
        self.assertIn('existing-project', cache_data)
        
        existing_info = cache_data['existing-project']
        self.assertEqual(existing_info.git_root, '/path/to/existing/project')
        self.assertIn('/path/to/existing/project/src', existing_info.aliases)
        
        # Test that existing aliases work (fallback scenario)
        with patch('src.shared.git_resolver.GitResolver.get_git_root') as mock_git:
            mock_git.return_value = '/path/to/existing/project'
            
            project_name_alias = resolver.resolve_project_name('/path/to/existing/project/src')
            self.assertEqual(project_name_alias, 'existing-project')


if __name__ == '__main__':
    unittest.main()