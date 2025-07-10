#!/usr/bin/env python3
"""
Tests for performance metrics collection in project name caching system.
"""
import unittest
import tempfile
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.performance_metrics import PerformanceMetrics
from shared.project_name_resolver import ProjectNameResolver


class TestPerformanceMetrics(unittest.TestCase):
    """Test cases for PerformanceMetrics class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = PerformanceMetrics()
    
    def test_initial_metrics_state(self):
        """Test that metrics start with zero values."""
        self.assertEqual(self.metrics.get_cache_hits(), 0)
        self.assertEqual(self.metrics.get_cache_misses(), 0)
        self.assertEqual(self.metrics.get_total_operations(), 0)
        self.assertEqual(self.metrics.get_hit_ratio(), 0.0)
    
    def test_record_cache_hit(self):
        """Test recording cache hits."""
        self.metrics.record_cache_hit()
        self.assertEqual(self.metrics.get_cache_hits(), 1)
        self.assertEqual(self.metrics.get_total_operations(), 1)
        self.assertEqual(self.metrics.get_hit_ratio(), 1.0)
    
    def test_record_cache_miss(self):
        """Test recording cache misses."""
        self.metrics.record_cache_miss()
        self.assertEqual(self.metrics.get_cache_misses(), 1)
        self.assertEqual(self.metrics.get_total_operations(), 1)
        self.assertEqual(self.metrics.get_hit_ratio(), 0.0)
    
    def test_hit_ratio_calculation(self):
        """Test hit ratio calculation with mixed hits and misses."""
        # Record 3 hits and 1 miss
        for _ in range(3):
            self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()
        
        self.assertEqual(self.metrics.get_cache_hits(), 3)
        self.assertEqual(self.metrics.get_cache_misses(), 1)
        self.assertEqual(self.metrics.get_total_operations(), 4)
        self.assertAlmostEqual(self.metrics.get_hit_ratio(), 0.75, places=2)
    
    def test_reset_metrics(self):
        """Test resetting metrics to zero."""
        self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()
        
        self.metrics.reset()
        
        self.assertEqual(self.metrics.get_cache_hits(), 0)
        self.assertEqual(self.metrics.get_cache_misses(), 0)
        self.assertEqual(self.metrics.get_total_operations(), 0)
        self.assertEqual(self.metrics.get_hit_ratio(), 0.0)
    
    def test_metrics_dict_export(self):
        """Test exporting metrics as dictionary."""
        self.metrics.record_cache_hit()
        self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()
        
        metrics_dict = self.metrics.to_dict()
        
        expected = {
            'cache_hits': 2,
            'cache_misses': 1,
            'total_operations': 3,
            'hit_ratio': 0.67
        }
        
        self.assertEqual(metrics_dict['cache_hits'], expected['cache_hits'])
        self.assertEqual(metrics_dict['cache_misses'], expected['cache_misses'])
        self.assertEqual(metrics_dict['total_operations'], expected['total_operations'])
        self.assertAlmostEqual(metrics_dict['hit_ratio'], expected['hit_ratio'], places=2)


class TestProjectNameResolverWithMetrics(unittest.TestCase):
    """Test ProjectNameResolver integration with performance metrics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, 'test_cache.json')
        self.resolver = ProjectNameResolver(self.cache_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_resolver_has_metrics(self):
        """Test that ProjectNameResolver has performance metrics."""
        self.assertIsNotNone(self.resolver.get_metrics())
        self.assertIsInstance(self.resolver.get_metrics(), PerformanceMetrics)
    
    def test_cache_hit_recorded(self):
        """Test that cache hits are recorded in metrics."""
        # First call will be a miss and populate cache
        test_path = '/test/project'
        self.resolver.resolve_project_name(test_path)
        
        # Reset metrics to track only the second call
        self.resolver.get_metrics().reset()
        
        # Second call should be a hit
        self.resolver.resolve_project_name(test_path)
        
        metrics = self.resolver.get_metrics()
        self.assertEqual(metrics.get_cache_hits(), 1)
        self.assertEqual(metrics.get_cache_misses(), 0)
    
    def test_cache_miss_recorded(self):
        """Test that cache misses are recorded in metrics."""
        test_path = '/test/new-project'
        
        # Fresh call should be a miss
        self.resolver.resolve_project_name(test_path)
        
        metrics = self.resolver.get_metrics()
        self.assertEqual(metrics.get_cache_hits(), 0)
        self.assertEqual(metrics.get_cache_misses(), 1)
    
    def test_multiple_operations_tracking(self):
        """Test tracking multiple cache operations."""
        paths = ['/test/project1', '/test/project2', '/test/project1', '/test/project2']
        
        for path in paths:
            self.resolver.resolve_project_name(path)
        
        metrics = self.resolver.get_metrics()
        # First 2 calls are misses, next 2 are hits
        self.assertEqual(metrics.get_cache_hits(), 2)
        self.assertEqual(metrics.get_cache_misses(), 2)
        self.assertEqual(metrics.get_total_operations(), 4)
        self.assertAlmostEqual(metrics.get_hit_ratio(), 0.5, places=2)


if __name__ == '__main__':
    unittest.main()