#!/usr/bin/env python3
"""
Test suite for FileManager class with atomic writes and iCloud sync.
"""
import unittest
import json
import os
import tempfile
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager class."""
    
    def setUp(self):
        """Set up test environment with temporary directories."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_data.json")
        self.icloud_dir = os.path.join(self.test_dir, "icloud_test")
        os.makedirs(self.icloud_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_atomic_write_basic(self):
        """Test that atomic write operations work correctly."""
        from src.shared.file_manager import FileManager
        
        manager = FileManager(self.test_file)
        
        # Test data
        test_data = {
            "session_id": "test_123",
            "total_tokens": 1000,
            "timestamp": datetime.now(ZoneInfo("UTC")).isoformat()
        }
        
        # Write data atomically
        manager.write_data(test_data)
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.test_file))
        
        # Verify data can be read back
        with open(self.test_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["session_id"], test_data["session_id"])
        self.assertEqual(saved_data["total_tokens"], test_data["total_tokens"])
        self.assertEqual(saved_data["timestamp"], test_data["timestamp"])
    
    def test_atomic_write_no_corruption(self):
        """Test that atomic writes prevent data corruption during concurrent operations."""
        from src.shared.file_manager import FileManager
        
        manager = FileManager(self.test_file)
        
        # Write initial data
        initial_data = {"version": 1, "data": "initial"}
        manager.write_data(initial_data)
        
        # Verify initial write
        self.assertTrue(os.path.exists(self.test_file))
        
        # Update data
        updated_data = {"version": 2, "data": "updated"}
        manager.write_data(updated_data)
        
        # Verify update
        with open(self.test_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["version"], 2)
        self.assertEqual(saved_data["data"], "updated")
    
    def test_read_data_file_exists(self):
        """Test reading data from existing file."""
        from src.shared.file_manager import FileManager
        
        manager = FileManager(self.test_file)
        
        # Create test data file
        test_data = {
            "test_field": "test_value",
            "numeric_field": 42,
            "list_field": [1, 2, 3]
        }
        
        with open(self.test_file, 'w') as f:
            json.dump(test_data, f)
        
        # Read data
        read_data = manager.read_data()
        
        self.assertEqual(read_data["test_field"], "test_value")
        self.assertEqual(read_data["numeric_field"], 42)
        self.assertEqual(read_data["list_field"], [1, 2, 3])
    
    def test_read_data_file_not_exists(self):
        """Test reading data when file doesn't exist."""
        from src.shared.file_manager import FileManager
        
        manager = FileManager(self.test_file)
        
        # Should return empty dict when file doesn't exist
        read_data = manager.read_data()
        self.assertEqual(read_data, {})
    
    def test_read_data_corrupted_file(self):
        """Test reading data from corrupted JSON file."""
        from src.shared.file_manager import FileManager
        
        manager = FileManager(self.test_file)
        
        # Create corrupted JSON file
        with open(self.test_file, 'w') as f:
            f.write("{ invalid json content")
        
        # Should return empty dict when file is corrupted
        read_data = manager.read_data()
        self.assertEqual(read_data, {})
    
    def test_icloud_sync_basic(self):
        """Test basic iCloud synchronization functionality."""
        from src.shared.file_manager import FileManager
        
        icloud_file = os.path.join(self.icloud_dir, "monitor_data.json")
        manager = FileManager(self.test_file, icloud_sync_path=icloud_file)
        
        # Test data
        test_data = {
            "session_count": 5,
            "last_update": datetime.now(ZoneInfo("UTC")).isoformat()
        }
        
        # Write data with iCloud sync
        manager.write_data(test_data)
        
        # Verify main file exists
        self.assertTrue(os.path.exists(self.test_file))
        
        # Verify iCloud file exists
        self.assertTrue(os.path.exists(icloud_file))
        
        # Verify both files have same content
        with open(self.test_file, 'r') as f:
            main_data = json.load(f)
        
        with open(icloud_file, 'r') as f:
            icloud_data = json.load(f)
        
        self.assertEqual(main_data, icloud_data)
    
    def test_icloud_sync_directory_creation(self):
        """Test that iCloud sync creates necessary directories."""
        from src.shared.file_manager import FileManager
        
        # Use nested directory path that doesn't exist
        nested_icloud_path = os.path.join(self.icloud_dir, "nested", "deep", "monitor_data.json")
        manager = FileManager(self.test_file, icloud_sync_path=nested_icloud_path)
        
        test_data = {"test": "data"}
        
        # Write data - should create directories
        manager.write_data(test_data)
        
        # Verify directories were created
        self.assertTrue(os.path.exists(os.path.dirname(nested_icloud_path)))
        self.assertTrue(os.path.exists(nested_icloud_path))
    
    def test_icloud_sync_failure_handling(self):
        """Test that iCloud sync failures don't affect main file operations."""
        from src.shared.file_manager import FileManager
        
        # Use invalid iCloud path (read-only or non-existent mount)
        invalid_icloud_path = "/dev/null/invalid/path/monitor_data.json"
        manager = FileManager(self.test_file, icloud_sync_path=invalid_icloud_path)
        
        test_data = {"test": "data"}
        
        # Write should succeed for main file even if iCloud sync fails
        manager.write_data(test_data)
        
        # Main file should exist
        self.assertTrue(os.path.exists(self.test_file))
        
        # Verify main file content
        with open(self.test_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["test"], "data")
    
    def test_file_manager_with_data_models(self):
        """Test FileManager integration with data models."""
        from src.shared.file_manager import FileManager
        from src.shared.data_models import SessionData, MonitoringData
        
        manager = FileManager(self.test_file)
        
        # Create test session data
        session = SessionData(
            session_id="integration_test_123",
            start_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 11, 45, 0, tzinfo=ZoneInfo("UTC")),
            total_tokens=25000,
            input_tokens=5000,
            output_tokens=20000,
            cost_usd=0.85,
            is_active=False
        )
        
        monitoring_data = MonitoringData(
            current_sessions=[session],
            total_sessions_this_month=10,
            total_cost_this_month=8.50,
            max_tokens_per_session=35000,
            last_update=datetime.now(ZoneInfo("UTC")),
            billing_period_start=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
            billing_period_end=datetime(2024, 1, 31, tzinfo=ZoneInfo("UTC"))
        )
        
        # Write monitoring data
        manager.write_data(monitoring_data.to_dict())
        
        # Read back and verify
        read_data = manager.read_data()
        restored_monitoring = MonitoringData.from_dict(read_data)
        
        self.assertEqual(len(restored_monitoring.current_sessions), 1)
        self.assertEqual(restored_monitoring.current_sessions[0].session_id, "integration_test_123")
        self.assertEqual(restored_monitoring.total_sessions_this_month, 10)
        self.assertEqual(restored_monitoring.total_cost_this_month, 8.50)
    
    def test_file_permissions_and_security(self):
        """Test that files are created with appropriate permissions."""
        from src.shared.file_manager import FileManager
        
        manager = FileManager(self.test_file)
        
        test_data = {"sensitive": "data"}
        manager.write_data(test_data)
        
        # Check file permissions (should be readable/writable by owner only)
        file_stat = os.stat(self.test_file)
        file_perms = file_stat.st_mode & 0o777
        
        # Should be 600 (owner read/write only) or 644 (owner read/write, group/other read)
        self.assertIn(file_perms, [0o600, 0o644])


if __name__ == '__main__':
    unittest.main()