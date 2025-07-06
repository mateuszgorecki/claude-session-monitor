#!/usr/bin/env python3
"""
Test suite for hook-related constants.
Following TDD approach - RED phase implementation.
"""
import unittest
import os
from pathlib import Path


class TestHookConstants(unittest.TestCase):
    """Test cases for hook-related constants."""
    
    def test_hook_constants_available(self):
        """Test that hook constants are available in constants module."""
        from src.shared.constants import (
            HOOK_LOG_DIR, 
            HOOK_LOG_FILE_PATTERN, 
            HOOK_LOG_RETENTION_DAYS,
            HOOK_LOG_MAX_SIZE_MB
        )
        
        # Test that constants are defined
        self.assertIsNotNone(HOOK_LOG_DIR)
        self.assertIsNotNone(HOOK_LOG_FILE_PATTERN)
        self.assertIsNotNone(HOOK_LOG_RETENTION_DAYS)
        self.assertIsNotNone(HOOK_LOG_MAX_SIZE_MB)
        
        # Test that constants have expected types
        self.assertIsInstance(HOOK_LOG_DIR, str)
        self.assertIsInstance(HOOK_LOG_FILE_PATTERN, str)
        self.assertIsInstance(HOOK_LOG_RETENTION_DAYS, int)
        self.assertIsInstance(HOOK_LOG_MAX_SIZE_MB, int)
    
    def test_activity_session_status_constants(self):
        """Test that activity session status constants are available."""
        from src.shared.constants import ACTIVITY_SESSION_STATUSES
        
        # Test that constant is defined
        self.assertIsNotNone(ACTIVITY_SESSION_STATUSES)
        self.assertIsInstance(ACTIVITY_SESSION_STATUSES, list)
        
        # Test that it contains expected values
        expected_statuses = ["ACTIVE", "WAITING", "STOPPED"]
        for status in expected_statuses:
            self.assertIn(status, ACTIVITY_SESSION_STATUSES)
    
    def test_hook_event_types(self):
        """Test that hook event type constants are available."""
        from src.shared.constants import HOOK_EVENT_TYPES
        
        # Test that constant is defined
        self.assertIsNotNone(HOOK_EVENT_TYPES)
        self.assertIsInstance(HOOK_EVENT_TYPES, list)
        
        # Test that it contains expected values
        expected_types = ["notification", "stop", "subagentstop"]
        for event_type in expected_types:
            self.assertIn(event_type, HOOK_EVENT_TYPES)
    
    def test_hook_configuration_constants(self):
        """Test that hook configuration constants are available."""
        from src.shared.constants import (
            HOOK_SCRIPTS_DIR,
            HOOK_CONFIG_FILE,
            HOOK_NOTIFICATION_SCRIPT,
            HOOK_STOP_SCRIPT
        )
        
        # Test that constants are defined
        self.assertIsNotNone(HOOK_SCRIPTS_DIR)
        self.assertIsNotNone(HOOK_CONFIG_FILE)
        self.assertIsNotNone(HOOK_NOTIFICATION_SCRIPT)
        self.assertIsNotNone(HOOK_STOP_SCRIPT)
        
        # Test that constants have expected types
        self.assertIsInstance(HOOK_SCRIPTS_DIR, str)
        self.assertIsInstance(HOOK_CONFIG_FILE, str)
        self.assertIsInstance(HOOK_NOTIFICATION_SCRIPT, str)
        self.assertIsInstance(HOOK_STOP_SCRIPT, str)


if __name__ == '__main__':
    unittest.main()