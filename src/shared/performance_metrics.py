#!/usr/bin/env python3
"""
Performance metrics collection for project name caching system.

This module provides comprehensive metrics tracking for cache operations,
including hit/miss ratios, operation counts, and performance analysis.
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timezone


class PerformanceMetrics:
    """
    Tracks performance metrics for cache operations.
    
    Provides detailed tracking of cache hit/miss ratios, operation counts,
    and timing information for performance analysis and optimization.
    """
    
    def __init__(self, logger_name: str = "project_cache") -> None:
        """
        Initialize performance metrics with zero values.
        
        Args:
            logger_name: Name for the logger instance
        """
        self._cache_hits = 0
        self._cache_misses = 0
        self._start_time = time.time()
        self._last_reset = datetime.now(timezone.utc)
        self._logger = logging.getLogger(logger_name)
        self._last_log_time = time.time()
        self._log_interval = 100  # Log every 100 operations
    
    def record_cache_hit(self) -> None:
        """Record a cache hit operation."""
        self._cache_hits += 1
        self._check_auto_log()
    
    def record_cache_miss(self) -> None:
        """Record a cache miss operation."""
        self._cache_misses += 1
        self._check_auto_log()
    
    def get_cache_hits(self) -> int:
        """Get total number of cache hits."""
        return self._cache_hits
    
    def get_cache_misses(self) -> int:
        """Get total number of cache misses."""
        return self._cache_misses
    
    def get_total_operations(self) -> int:
        """Get total number of cache operations (hits + misses)."""
        return self._cache_hits + self._cache_misses
    
    def get_hit_ratio(self) -> float:
        """
        Get cache hit ratio as a percentage.
        
        Returns:
            Hit ratio from 0.0 to 1.0, or 0.0 if no operations recorded
        """
        total = self.get_total_operations()
        if total == 0:
            return 0.0
        return round(self._cache_hits / total, 2)
    
    def reset(self) -> None:
        """Reset all metrics to zero."""
        self._cache_hits = 0
        self._cache_misses = 0
        self._start_time = time.time()
        self._last_reset = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, float]:
        """
        Export metrics as dictionary for logging and analysis.
        
        Returns:
            Dictionary containing all current metrics
        """
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'total_operations': self.get_total_operations(),
            'hit_ratio': self.get_hit_ratio(),
            'uptime_seconds': round(time.time() - self._start_time, 2),
            'last_reset': self._last_reset.isoformat()
        }
    
    def get_performance_summary(self) -> str:
        """
        Get human-readable performance summary.
        
        Returns:
            Formatted string with key performance metrics
        """
        total = self.get_total_operations()
        if total == 0:
            return "No cache operations recorded"
        
        hit_ratio = self.get_hit_ratio()
        uptime = round(time.time() - self._start_time, 2)
        
        return (f"Cache Performance: {hit_ratio:.1%} hit ratio "
                f"({self._cache_hits} hits, {self._cache_misses} misses) "
                f"over {total} operations in {uptime}s")
    
    def _check_auto_log(self) -> None:
        """Check if we should automatically log performance metrics."""
        total_ops = self.get_total_operations()
        if total_ops > 0 and total_ops % self._log_interval == 0:
            self.log_performance()
    
    def log_performance(self, level: int = logging.INFO) -> None:
        """
        Log current performance metrics.
        
        Args:
            level: Logging level to use (default: INFO)
        """
        if not self._logger.isEnabledFor(level):
            return
            
        total_ops = self.get_total_operations()
        if total_ops == 0:
            self._logger.log(level, "Project cache: No operations recorded yet")
            return
        
        hit_ratio = self.get_hit_ratio()
        uptime = round(time.time() - self._start_time, 1)
        
        self._logger.log(level, 
            f"Project cache performance: {hit_ratio:.1%} hit ratio "
            f"({self._cache_hits} hits, {self._cache_misses} misses) "
            f"over {total_ops} operations in {uptime}s"
        )
    
    def set_log_interval(self, interval: int) -> None:
        """
        Set the automatic logging interval.
        
        Args:
            interval: Number of operations between automatic logs
        """
        self._log_interval = max(1, interval)