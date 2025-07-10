#!/usr/bin/env python3
"""
Memory management for project name caching system.

This module provides memory management capabilities including cache size monitoring,
LRU-based cleanup strategies, and automatic memory optimization.
"""
import logging
from typing import Dict, List, Tuple
from datetime import datetime

from .project_models import ProjectInfo, ProjectCache
from .constants import (
    MAX_CACHE_ENTRIES, CACHE_CLEANUP_THRESHOLD, CACHE_SIZE_WARNING_THRESHOLD,
    CACHE_CLEANUP_BATCH_SIZE, MIN_CACHE_RETENTION_HOURS, AGGRESSIVE_CLEANUP_THRESHOLD
)


class MemoryManager:
    """
    Manages memory usage for project name cache.
    
    Provides cache size monitoring, automatic cleanup based on LRU strategy,
    and memory optimization to prevent unbounded cache growth.
    """
    
    def __init__(self, cache: ProjectCache, max_entries: int = MAX_CACHE_ENTRIES) -> None:
        """
        Initialize MemoryManager with cache instance and limits.
        
        Args:
            cache: ProjectCache instance to manage
            max_entries: Maximum number of entries allowed in cache
        """
        self.cache = cache
        self.max_entries = max_entries
        self.logger = logging.getLogger("memory_manager")
        self._last_cleanup_time = datetime.now()
    
    def get_cache_size(self) -> int:
        """
        Get current number of entries in cache.
        
        Returns:
            Number of cached project entries
        """
        cache_data = self.cache.load()
        return len(cache_data)
    
    def get_max_entries(self) -> int:
        """
        Get maximum allowed cache entries.
        
        Returns:
            Maximum number of entries allowed
        """
        return self.max_entries
    
    def needs_cleanup(self) -> bool:
        """
        Check if cache cleanup is needed.
        
        Returns:
            True if cache size exceeds maximum allowed entries
        """
        return self.get_cache_size() > self.max_entries
    
    def should_warn(self) -> bool:
        """
        Check if cache size should trigger a warning.
        
        Returns:
            True if cache size approaches the limit
        """
        current_size = self.get_cache_size()
        warning_threshold = min(self.max_entries * 0.8, CACHE_SIZE_WARNING_THRESHOLD)
        return current_size >= warning_threshold
    
    def cleanup_cache(self) -> Dict[str, ProjectInfo]:
        """
        Perform LRU-based cache cleanup.
        
        Removes least recently used entries to bring cache size within limits.
        Preserves all aliases for remaining entries.
        
        Returns:
            Cleaned cache data with remaining entries
        """
        cache_data = self.cache.load()
        current_size = len(cache_data)
        
        if current_size <= self.max_entries:
            self.logger.debug(f"Cache cleanup not needed: {current_size} <= {self.max_entries}")
            return cache_data
        
        # Sort projects by last_accessed time (oldest first)
        sorted_projects = sorted(
            cache_data.items(),
            key=lambda item: item[1].last_accessed
        )
        
        # Keep only the most recently used entries
        entries_to_remove = current_size - self.max_entries
        projects_to_keep = sorted_projects[entries_to_remove:]
        
        # Create cleaned cache data
        cleaned_data = dict(projects_to_keep)
        
        # Save cleaned cache
        self.cache.save(cleaned_data)
        
        # Log cleanup operation
        removed_count = len(sorted_projects) - len(projects_to_keep)
        self.logger.info(
            f"Cache cleanup completed: removed {removed_count} entries, "
            f"kept {len(cleaned_data)} most recent entries"
        )
        
        self._last_cleanup_time = datetime.now()
        return cleaned_data
    
    def get_cleanup_summary(self) -> str:
        """
        Get human-readable summary of cache state and cleanup needs.
        
        Returns:
            Formatted string describing cache memory status
        """
        current_size = self.get_cache_size()
        
        if current_size <= self.max_entries:
            return (f"Cache memory: {current_size} entries (limit: {self.max_entries}) - OK")
        else:
            excess = current_size - self.max_entries
            return (f"Cache memory: {current_size} entries (limit: {self.max_entries}) - "
                   f"cleanup needed ({excess} excess entries)")
    
    def get_memory_stats(self) -> Dict[str, int]:
        """
        Get detailed memory statistics.
        
        Returns:
            Dictionary with memory usage statistics
        """
        current_size = self.get_cache_size()
        return {
            'current_entries': current_size,
            'max_entries': self.max_entries,
            'available_slots': max(0, self.max_entries - current_size),
            'excess_entries': max(0, current_size - self.max_entries),
            'utilization_percent': round((current_size / self.max_entries) * 100, 1)
        }
    
    def log_memory_status(self, level: int = logging.INFO) -> None:
        """
        Log current memory status.
        
        Args:
            level: Logging level to use
        """
        if not self.logger.isEnabledFor(level):
            return
        
        stats = self.get_memory_stats()
        
        self.logger.log(level,
            f"Cache memory status: {stats['current_entries']}/{stats['max_entries']} entries "
            f"({stats['utilization_percent']}% utilized)"
        )
        
        if self.needs_cleanup():
            self.logger.warning(
                f"Cache cleanup needed: {stats['excess_entries']} excess entries"
            )
        elif self.should_warn():
            self.logger.warning(
                f"Cache approaching limit: {stats['available_slots']} slots remaining"
            )
    
    def optimize_memory(self) -> str:
        """
        Perform comprehensive memory optimization.
        
        Returns:
            Summary of optimization actions taken
        """
        initial_size = self.get_cache_size()
        
        if not self.needs_cleanup():
            return f"Memory optimization: no action needed ({initial_size} entries)"
        
        # Perform cleanup
        cleaned_data = self.cleanup_cache()
        final_size = len(cleaned_data)
        removed_count = initial_size - final_size
        
        return (f"Memory optimization: removed {removed_count} LRU entries, "
                f"cache size: {initial_size} → {final_size}")
    
    def smart_cleanup(self) -> Dict[str, ProjectInfo]:
        """
        Perform intelligent cleanup based on cache state and usage patterns.
        
        Uses adaptive strategies based on cache size and system state.
        
        Returns:
            Cleaned cache data
        """
        cache_data = self.cache.load()
        current_size = len(cache_data)
        
        if current_size <= self.max_entries:
            return cache_data
        
        # Determine cleanup strategy based on cache state
        if current_size >= self.max_entries * AGGRESSIVE_CLEANUP_THRESHOLD:
            # Aggressive cleanup - remove more entries
            target_size = int(self.max_entries * 0.7)  # Clean to 70% capacity
            self.logger.info(f"Performing aggressive cleanup to {target_size} entries")
        else:
            # Conservative cleanup - just bring within limits
            target_size = self.max_entries
        
        # Filter out entries that are too new to be removed
        from datetime import timezone
        now = datetime.now(timezone.utc)
        retention_cutoff = now.timestamp() - (MIN_CACHE_RETENTION_HOURS * 3600)
        
        # Separate entries into cleanable and protected
        cleanable_entries = []
        protected_entries = []
        
        for name, info in cache_data.items():
            if info.last_accessed.timestamp() < retention_cutoff:
                cleanable_entries.append((name, info))
            else:
                protected_entries.append((name, info))
        
        # If we have enough protected entries, we can't clean much
        if len(protected_entries) >= target_size:
            self.logger.warning(
                f"Cannot cleanup cache: {len(protected_entries)} entries are too recent to remove"
            )
            return cache_data
        
        # Sort cleanable entries by last accessed (oldest first)
        cleanable_entries.sort(key=lambda item: item[1].last_accessed)
        
        # Calculate how many cleanable entries to keep
        entries_to_keep_from_cleanable = target_size - len(protected_entries)
        kept_cleanable = cleanable_entries[-entries_to_keep_from_cleanable:] if entries_to_keep_from_cleanable > 0 else []
        
        # Combine protected and kept cleanable entries
        final_entries = dict(protected_entries + kept_cleanable)
        
        # Save cleaned cache
        self.cache.save(final_entries)
        
        removed_count = current_size - len(final_entries)
        self.logger.info(
            f"Smart cleanup: removed {removed_count} entries, "
            f"kept {len(protected_entries)} protected, {len(kept_cleanable)} cleanable"
        )
        
        return final_entries
    
    def get_cache_health_report(self) -> Dict[str, any]:
        """
        Generate comprehensive cache health report.
        
        Returns:
            Dictionary with detailed cache health metrics
        """
        cache_data = self.cache.load()
        current_size = len(cache_data)
        
        if current_size == 0:
            return {
                'status': 'empty',
                'size': 0,
                'health_score': 100,
                'recommendations': ['Cache is empty - no action needed']
            }
        
        # Calculate health metrics
        utilization = (current_size / self.max_entries) * 100
        
        # Analyze entry ages
        from datetime import timezone
        now = datetime.now(timezone.utc)
        ages = [(now - info.last_accessed).total_seconds() / 3600 for info in cache_data.values()]
        avg_age_hours = sum(ages) / len(ages)
        old_entries = sum(1 for age in ages if age > MIN_CACHE_RETENTION_HOURS)
        
        # Calculate health score (0-100)
        health_score = 100
        if utilization > 90:
            health_score -= 30
        elif utilization > 80:
            health_score -= 15
        
        if avg_age_hours > MIN_CACHE_RETENTION_HOURS * 2:
            health_score -= 20
        
        if old_entries > current_size * 0.5:
            health_score -= 25
        
        health_score = max(0, health_score)
        
        # Generate recommendations
        recommendations = []
        if utilization > 90:
            recommendations.append("Cache is critically full - immediate cleanup recommended")
        elif utilization > 80:
            recommendations.append("Cache is nearly full - cleanup recommended soon")
        
        if old_entries > current_size * 0.3:
            recommendations.append(f"{old_entries} entries are older than {MIN_CACHE_RETENTION_HOURS}h - cleanup beneficial")
        
        if not recommendations:
            recommendations.append("Cache health is good - no immediate action needed")
        
        # Determine status
        if health_score >= 80:
            status = 'healthy'
        elif health_score >= 60:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'health_score': health_score,
            'size': current_size,
            'max_size': self.max_entries,
            'utilization_percent': round(utilization, 1),
            'avg_age_hours': round(avg_age_hours, 1),
            'old_entries': old_entries,
            'recommendations': recommendations
        }