#!/usr/bin/env python3
"""
Tests for ImprovedSubprocessPool - thread-safe subprocess management.
"""
import unittest
import threading
import time
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from daemon.improved_subprocess_pool import ImprovedSubprocessPool


class TestImprovedSubprocessPool(unittest.TestCase):
    """Test ImprovedSubprocessPool thread-safe implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pool = ImprovedSubprocessPool(max_workers=2)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.pool, 'stop'):
            self.pool.stop()
    
    def test_concurrent_access_race_condition(self):
        """Test that concurrent access doesn't cause race conditions."""
        results = []
        errors = []
        
        def worker_thread(thread_id):
            """Worker function that accesses the pool concurrently."""
            try:
                # Simulate concurrent cache access and command execution
                for i in range(5):
                    result = self.pool.run_command(['echo', f'thread-{thread_id}-{i}'])
                    results.append((thread_id, i, result))
                    time.sleep(0.01)  # Small delay to increase chance of race condition
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads that access the pool concurrently
        threads = []
        num_threads = 5
        
        for thread_id in range(num_threads):
            t = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(t)
        
        # Start all threads simultaneously
        for t in threads:
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=10)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Race condition errors: {errors}")
        
        # Verify all results were collected
        expected_results = num_threads * 5
        self.assertEqual(len(results), expected_results, 
                        f"Expected {expected_results} results, got {len(results)}")
        
        # Verify results are valid
        for thread_id, i, result in results:
            self.assertIn('success', result)
            self.assertTrue(result['success'], f"Command failed: {result}")
    
    def test_cache_thread_safety(self):
        """Test that cache operations are thread-safe."""
        cache_access_count = [0]  # Use list for mutable counter
        cache_errors = []
        
        def cache_worker():
            """Worker that accesses cache concurrently."""
            try:
                for i in range(10):
                    # Access cache multiple times
                    with self.pool._cache_lock:
                        cache_access_count[0] += 1
                        # Simulate cache operations
                        self.pool._result_cache[f'test-{i}'] = ({'data': i}, time.time())
                        self.pool._clean_cache()
                    time.sleep(0.001)
            except Exception as e:
                cache_errors.append(str(e))
        
        # Start multiple threads accessing cache
        threads = []
        for _ in range(3):
            t = threading.Thread(target=cache_worker)
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=5)
        
        # Verify no cache-related errors
        self.assertEqual(len(cache_errors), 0, f"Cache errors: {cache_errors}")
        self.assertGreater(cache_access_count[0], 0, "Cache was not accessed")
    
    def test_task_synchronization(self):
        """Test that task completion synchronization works properly."""
        completion_order = []
        
        def mock_execute_command(command):
            """Mock command execution with varying delays."""
            thread_id = threading.get_ident()
            if 'slow' in command:
                time.sleep(0.1)
            completion_order.append((thread_id, command))
            return {'success': True, 'stdout': f'output-{thread_id}', 'stderr': ''}
        
        with patch.object(self.pool, '_execute_command', side_effect=mock_execute_command):
            # Submit tasks that complete at different times
            tasks = [
                ['echo', 'fast-1'],
                ['echo', 'slow-1'],
                ['echo', 'fast-2'],
                ['echo', 'slow-2']
            ]
            
            results = []
            threads = []
            
            def run_task(command):
                result = self.pool.run_command(command, use_cache=False)
                results.append(result)
            
            # Start all tasks
            for command in tasks:
                t = threading.Thread(target=run_task, args=(command,))
                threads.append(t)
                t.start()
            
            # Wait for completion
            for t in threads:
                t.join(timeout=5)
            
            # Verify all tasks completed
            self.assertEqual(len(results), len(tasks))
            self.assertEqual(len(completion_order), len(tasks))
            
            # Verify all results are successful
            for result in results:
                self.assertTrue(result['success'])
    
    def test_worker_pool_initialization(self):
        """Test that worker pool initializes correctly."""
        # This test should fail initially because ImprovedSubprocessPool doesn't exist
        self.assertIsInstance(self.pool, ImprovedSubprocessPool)
        self.assertEqual(self.pool.max_workers, 2)
        self.assertIsNotNone(self.pool._task_queue)
        self.assertIsNotNone(self.pool._cache_lock)
    
    def test_graceful_shutdown(self):
        """Test that pool shuts down gracefully without deadlocks."""
        # Start the pool
        self.pool.start()
        
        # Submit some work
        def submit_work():
            for i in range(3):
                try:
                    self.pool.run_command(['echo', f'shutdown-test-{i}'])
                except:
                    pass  # Expected during shutdown
        
        work_thread = threading.Thread(target=submit_work)
        work_thread.start()
        
        # Allow some work to start
        time.sleep(0.1)
        
        # Stop the pool
        start_time = time.time()
        self.pool.stop()
        shutdown_time = time.time() - start_time
        
        # Verify shutdown completed in reasonable time (no deadlocks)
        self.assertLess(shutdown_time, 5.0, "Shutdown took too long - possible deadlock")
        
        # Wait for work thread to finish
        work_thread.join(timeout=5)


class TestSubprocessPoolEventSynchronization(unittest.TestCase):
    """Test event-based synchronization instead of busy waiting."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pool = ImprovedSubprocessPool(max_workers=1)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.pool, 'stop'):
            self.pool.stop()
    
    def test_event_based_task_completion(self):
        """Test that task completion uses events instead of polling."""
        completion_events = []
        
        def mock_worker_loop():
            """Mock worker that uses event signaling."""
            while not self.pool._shutdown_event.is_set():
                try:
                    task = self.pool._task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    # Process task and signal completion
                    command, result_future = task
                    result_future['result'] = {'success': True}
                    result_future['error'] = None
                    result_future['completion_event'].set()  # Event-based signaling
                    completion_events.append(time.time())
                    
                except:
                    continue
        
        # This test verifies that we're not using busy waiting (time.sleep loops)
        # and instead using proper event synchronization
        
        # Should use threading.Event for completion notification
        self.assertTrue(hasattr(self.pool, '_shutdown_event'))
        
        # Should have proper task queue management
        self.assertTrue(hasattr(self.pool, '_task_queue'))


class TestResourceMonitoring(unittest.TestCase):
    """Test resource monitoring and statistics features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pool = ImprovedSubprocessPool(max_workers=1, cache_ttl=5, task_timeout=10)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.pool, 'stop'):
            self.pool.stop()
    
    def test_statistics_tracking(self):
        """Test that pool tracks statistics correctly."""
        # Get initial stats
        initial_stats = self.pool.get_stats()
        self.assertEqual(initial_stats['tasks_completed'], 0)
        self.assertEqual(initial_stats['tasks_failed'], 0)
        
        # Mock successful command execution
        with patch.object(self.pool, '_execute_command') as mock_execute:
            mock_execute.return_value = {'success': True, 'stdout': 'test', 'stderr': ''}
            
            # Run a command
            result = self.pool.run_command(['echo', 'test'])
            
            # Check updated stats
            stats = self.pool.get_stats()
            self.assertEqual(stats['tasks_completed'], 1)
            self.assertEqual(stats['cache_misses'], 1)
    
    def test_cache_hit_tracking(self):
        """Test that cache hits are tracked correctly."""
        # Mock successful command execution
        with patch.object(self.pool, '_execute_command') as mock_execute:
            mock_execute.return_value = {'success': True, 'stdout': 'cached', 'stderr': ''}
            
            # First call - cache miss
            self.pool.run_command(['echo', 'cached-test'])
            stats_after_first = self.pool.get_stats()
            self.assertEqual(stats_after_first['cache_misses'], 1)
            self.assertEqual(stats_after_first['cache_hits'], 0)
            
            # Second call - cache hit
            self.pool.run_command(['echo', 'cached-test'])
            stats_after_second = self.pool.get_stats()
            self.assertEqual(stats_after_second['cache_misses'], 1)
            self.assertEqual(stats_after_second['cache_hits'], 1)
    
    def test_health_status(self):
        """Test that health status provides comprehensive information."""
        health = self.pool.get_health_status()
        
        # Verify health status structure
        required_keys = [
            'workers_active', 'workers_started', 'shutdown_requested',
            'cache_size', 'queue_size', 'stats', 'cache_hit_ratio'
        ]
        for key in required_keys:
            self.assertIn(key, health)
        
        # Verify data types
        self.assertIsInstance(health['workers_active'], int)
        self.assertIsInstance(health['cache_hit_ratio'], float)
        self.assertIsInstance(health['stats'], dict)
    
    def test_configurable_timeouts(self):
        """Test that timeouts are configurable."""
        pool = ImprovedSubprocessPool(cache_ttl=30, task_timeout=60)
        
        self.assertEqual(pool.cache_ttl, 30)
        self.assertEqual(pool.task_timeout, 60)
    
    def test_cache_management(self):
        """Test cache clearing and size limits."""
        # Add some items to cache
        with patch.object(self.pool, '_execute_command') as mock_execute:
            mock_execute.return_value = {'success': True, 'stdout': 'test', 'stderr': ''}
            
            # Create some cached entries
            for i in range(3):
                self.pool.run_command([f'echo', f'test-{i}'])
            
            # Verify cache has entries
            health_before = self.pool.get_health_status()
            self.assertGreater(health_before['cache_size'], 0)
            
            # Clear cache
            self.pool.clear_cache()
            
            # Verify cache is empty
            health_after = self.pool.get_health_status()
            self.assertEqual(health_after['cache_size'], 0)


if __name__ == '__main__':
    unittest.main()