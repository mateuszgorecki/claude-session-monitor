#!/usr/bin/env python3

import unittest
import json
import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, mock_open

from src.client.data_reader import DataReader
from src.shared.data_models import MonitoringData, SessionData, ConfigData, ErrorStatus


class TestDataReader(unittest.TestCase):
    """Test suite for DataReader class following TDD approach."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "monitor_data.json")
        
        # Create sample monitoring data
        self.sample_session = SessionData(
            session_id="test-session-1",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            total_tokens=1000,
            input_tokens=400,
            output_tokens=600,
            cost_usd=2.50,
            is_active=True
        )
        
        self.sample_config = ConfigData(
            billing_start_day=15,
            total_monthly_sessions=50,
            time_remaining_alert_minutes=30,
            inactivity_alert_minutes=10,
            ccusage_fetch_interval_seconds=10
        )
        
        self.sample_monitoring_data = MonitoringData(
            current_sessions=[self.sample_session],
            total_sessions_this_month=1,
            total_cost_this_month=2.50,
            max_tokens_per_session=1000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
        )

    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        os.rmdir(self.temp_dir)

    def test_read_data_success(self):
        """Test successful reading of monitoring data from file."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        # Create reader and read data
        reader = DataReader(self.test_file_path)
        data = reader.read_data()
        
        # Verify data was read correctly
        self.assertIsInstance(data, MonitoringData)
        self.assertEqual(data.total_sessions_this_month, 1)
        self.assertEqual(data.total_cost_this_month, 2.50)
        self.assertEqual(len(data.current_sessions), 1)

    def test_read_data_file_not_found(self):
        """Test graceful handling when data file doesn't exist."""
        reader = DataReader("/nonexistent/path/monitor_data.json")
        data = reader.read_data()
        
        # Should return None when file doesn't exist
        self.assertIsNone(data)

    def test_read_data_invalid_json(self):
        """Test handling of corrupted JSON file."""
        # Write invalid JSON to file
        with open(self.test_file_path, 'w') as f:
            f.write("{ invalid json content")
        
        reader = DataReader(self.test_file_path)
        data = reader.read_data()
        
        # Should return None for invalid JSON
        self.assertIsNone(data)

    def test_read_data_caching(self):
        """Test that data is cached and not re-read unnecessarily."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        reader = DataReader(self.test_file_path, cache_duration=1.0)
        
        # First read
        data1 = reader.read_data()
        self.assertIsNotNone(data1)
        
        # Modify file
        modified_data = self.sample_monitoring_data.to_dict()
        modified_data['total_sessions_this_month'] = 999
        with open(self.test_file_path, 'w') as f:
            json.dump(modified_data, f)
        
        # Second read (should return cached data)
        data2 = reader.read_data()
        self.assertEqual(data2.total_sessions_this_month, 1)  # Original cached value
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Third read (should read new data)
        data3 = reader.read_data()
        self.assertEqual(data3.total_sessions_this_month, 999)  # Updated value

    def test_is_daemon_running_fresh_file(self):
        """Test daemon detection when file was recently updated."""
        # Write test data with recent timestamp
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        reader = DataReader(self.test_file_path)
        self.assertTrue(reader.is_daemon_running())

    def test_is_daemon_running_stale_file(self):
        """Test daemon detection when file is stale."""
        # Write test data
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        # Make file appear old by setting modification time in the past
        old_time = time.time() - 120  # 2 minutes ago
        os.utime(self.test_file_path, (old_time, old_time))
        
        reader = DataReader(self.test_file_path, daemon_timeout=60)
        self.assertFalse(reader.is_daemon_running())

    def test_is_daemon_running_no_file(self):
        """Test daemon detection when file doesn't exist."""
        reader = DataReader("/nonexistent/path/monitor_data.json")
        self.assertFalse(reader.is_daemon_running())

    def test_get_file_age(self):
        """Test file age calculation."""
        # Create file
        with open(self.test_file_path, 'w') as f:
            f.write("{}")
        
        reader = DataReader(self.test_file_path)
        age = reader.get_file_age()
        
        # File should be very recent (less than 5 seconds old)
        self.assertLess(age, 5.0)

    def test_get_file_age_no_file(self):
        """Test file age when file doesn't exist."""
        reader = DataReader("/nonexistent/path/monitor_data.json")
        age = reader.get_file_age()
        
        # Should return very large value for missing file
        self.assertGreaterEqual(age, 999999)

    def test_force_refresh(self):
        """Test forcing cache refresh."""
        # Write test data to file
        with open(self.test_file_path, 'w') as f:
            json.dump(self.sample_monitoring_data.to_dict(), f)
        
        reader = DataReader(self.test_file_path, cache_duration=60.0)  # Long cache
        
        # First read
        data1 = reader.read_data()
        self.assertEqual(data1.total_sessions_this_month, 1)
        
        # Modify file
        modified_data = self.sample_monitoring_data.to_dict()
        modified_data['total_sessions_this_month'] = 555
        with open(self.test_file_path, 'w') as f:
            json.dump(modified_data, f)
        
        # Normal read (should return cached data)
        data2 = reader.read_data()
        self.assertEqual(data2.total_sessions_this_month, 1)
        
        # Force refresh
        data3 = reader.read_data(force_refresh=True)
        self.assertEqual(data3.total_sessions_this_month, 555)


if __name__ == '__main__':
    unittest.main()