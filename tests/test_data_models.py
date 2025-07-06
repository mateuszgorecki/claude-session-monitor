#!/usr/bin/env python3
"""
Test suite for data models used in the Claude session monitor.
Following TDD approach - these tests define the expected behavior before implementation.
"""
import unittest
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class TestSessionData(unittest.TestCase):
    """Test cases for SessionData model."""
    
    def test_session_data_serialization(self):
        """Test that SessionData can be serialized to JSON and deserialized back."""
        # This will fail initially - that's expected in RED phase
        from src.shared.data_models import SessionData
        
        # Create a session data instance
        session = SessionData(
            session_id="test_session_123",
            start_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 11, 45, 0, tzinfo=ZoneInfo("UTC")),
            total_tokens=25000,
            input_tokens=5000,
            output_tokens=20000,
            cost_usd=0.85,
            is_active=False
        )
        
        # Test serialization
        json_data = session.to_json()
        self.assertIsInstance(json_data, str)
        
        # Test that JSON is valid
        parsed = json.loads(json_data)
        self.assertIn("session_id", parsed)
        self.assertIn("start_time", parsed)
        self.assertIn("total_tokens", parsed)
        
        # Test deserialization
        restored_session = SessionData.from_json(json_data)
        self.assertEqual(restored_session.session_id, session.session_id)
        self.assertEqual(restored_session.total_tokens, session.total_tokens)
        self.assertEqual(restored_session.cost_usd, session.cost_usd)
        self.assertEqual(restored_session.is_active, session.is_active)
    
    def test_session_data_dict_conversion(self):
        """Test that SessionData can be converted to/from dictionary."""
        from src.shared.data_models import SessionData
        
        session = SessionData(
            session_id="dict_test_456",
            start_time=datetime(2024, 1, 15, 14, 20, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 15, 30, 0, tzinfo=ZoneInfo("UTC")),
            total_tokens=15000,
            input_tokens=3000,
            output_tokens=12000,
            cost_usd=0.45,
            is_active=True
        )
        
        # Convert to dict
        data_dict = session.to_dict()
        self.assertIsInstance(data_dict, dict)
        self.assertEqual(data_dict["session_id"], "dict_test_456")
        self.assertEqual(data_dict["total_tokens"], 15000)
        
        # Convert from dict
        restored_session = SessionData.from_dict(data_dict)
        self.assertEqual(restored_session.session_id, session.session_id)
        self.assertEqual(restored_session.total_tokens, session.total_tokens)
        self.assertEqual(restored_session.is_active, session.is_active)


class TestMonitoringData(unittest.TestCase):
    """Test cases for MonitoringData model."""
    
    def test_monitoring_data_creation(self):
        """Test that MonitoringData can be created with all required fields."""
        from src.shared.data_models import MonitoringData, SessionData
        
        # Create some sample sessions
        sessions = [
            SessionData(
                session_id="session_1",
                start_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=ZoneInfo("UTC")),
                end_time=datetime(2024, 1, 15, 11, 0, 0, tzinfo=ZoneInfo("UTC")),
                total_tokens=10000,
                input_tokens=2000,
                output_tokens=8000,
                cost_usd=0.30,
                is_active=False
            ),
            SessionData(
                session_id="session_2",
                start_time=datetime(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
                end_time=None,  # Active session
                total_tokens=5000,
                input_tokens=1000,
                output_tokens=4000,
                cost_usd=0.15,
                is_active=True
            )
        ]
        
        monitoring_data = MonitoringData(
            current_sessions=sessions,
            total_sessions_this_month=25,
            total_cost_this_month=12.50,
            max_tokens_per_session=35000,
            last_update=datetime.now(ZoneInfo("UTC")),
            billing_period_start=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
            billing_period_end=datetime(2024, 1, 31, tzinfo=ZoneInfo("UTC"))
        )
        
        self.assertEqual(len(monitoring_data.current_sessions), 2)
        self.assertEqual(monitoring_data.total_sessions_this_month, 25)
        self.assertEqual(monitoring_data.total_cost_this_month, 12.50)
        self.assertEqual(monitoring_data.max_tokens_per_session, 35000)
    
    def test_monitoring_data_json_serialization(self):
        """Test that MonitoringData can be serialized to JSON."""
        from src.shared.data_models import MonitoringData
        
        monitoring_data = MonitoringData(
            current_sessions=[],
            total_sessions_this_month=10,
            total_cost_this_month=5.75,
            max_tokens_per_session=30000,
            last_update=datetime.now(ZoneInfo("UTC")),
            billing_period_start=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
            billing_period_end=datetime(2024, 1, 31, tzinfo=ZoneInfo("UTC"))
        )
        
        json_data = monitoring_data.to_json()
        self.assertIsInstance(json_data, str)
        
        # Verify JSON structure
        parsed = json.loads(json_data)
        self.assertIn("current_sessions", parsed)
        self.assertIn("total_sessions_this_month", parsed)
        self.assertIn("total_cost_this_month", parsed)
        self.assertIn("last_update", parsed)
    
    def test_monitoring_data_with_activity_sessions(self):
        """Test that MonitoringData can contain activity sessions."""
        from src.shared.data_models import MonitoringData, SessionData, ActivitySessionData
        
        # Create sample sessions
        session = SessionData(
            session_id="billing_session",
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=ZoneInfo("UTC")),
            end_time=None,
            total_tokens=1000,
            input_tokens=300,
            output_tokens=700,
            cost_usd=0.05,
            is_active=True
        )
        
        activity_session = ActivitySessionData(
            session_id="activity_session",
            start_time=datetime(2024, 1, 15, 10, 30, tzinfo=ZoneInfo("UTC")),
            status="ACTIVE",
            event_type="notification"
        )
        
        # Create monitoring data with activity sessions
        monitoring_data = MonitoringData(
            current_sessions=[session],
            activity_sessions=[activity_session],
            total_sessions_this_month=1,
            total_cost_this_month=0.05,
            max_tokens_per_session=1000,
            last_update=datetime.now(ZoneInfo("UTC")),
            billing_period_start=datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC")),
            billing_period_end=datetime(2024, 2, 1, tzinfo=ZoneInfo("UTC"))
        )
        
        # Test serialization includes activity sessions
        data_dict = monitoring_data.to_dict()
        self.assertIn("activity_sessions", data_dict)
        self.assertEqual(len(data_dict["activity_sessions"]), 1)
        self.assertEqual(data_dict["activity_sessions"][0]["session_id"], "activity_session")
        
        # Test deserialization
        restored_data = MonitoringData.from_dict(data_dict)
        self.assertEqual(len(restored_data.activity_sessions), 1)
        self.assertEqual(restored_data.activity_sessions[0].session_id, "activity_session")
        self.assertEqual(restored_data.activity_sessions[0].status, "ACTIVE")


class TestConfigData(unittest.TestCase):
    """Test cases for ConfigData model."""
    
    def test_config_data_with_defaults(self):
        """Test that ConfigData uses proper default values."""
        from src.shared.data_models import ConfigData
        
        config = ConfigData()
        
        # Check default values based on current implementation
        self.assertEqual(config.total_monthly_sessions, 50)
        self.assertEqual(config.refresh_interval_seconds, 1)
        self.assertEqual(config.ccusage_fetch_interval_seconds, 10)
        self.assertEqual(config.time_remaining_alert_minutes, 30)
        self.assertEqual(config.inactivity_alert_minutes, 10)
        self.assertEqual(config.local_timezone, "Europe/Warsaw")
    
    def test_config_data_custom_values(self):
        """Test that ConfigData accepts custom values."""
        from src.shared.data_models import ConfigData
        
        config = ConfigData(
            total_monthly_sessions=100,
            refresh_interval_seconds=2,
            ccusage_fetch_interval_seconds=15,
            time_remaining_alert_minutes=45,
            inactivity_alert_minutes=15,
            local_timezone="America/New_York",
            billing_start_day=15
        )
        
        self.assertEqual(config.total_monthly_sessions, 100)
        self.assertEqual(config.refresh_interval_seconds, 2)
        self.assertEqual(config.ccusage_fetch_interval_seconds, 15)
        self.assertEqual(config.time_remaining_alert_minutes, 45)
        self.assertEqual(config.inactivity_alert_minutes, 15)
        self.assertEqual(config.local_timezone, "America/New_York")
        self.assertEqual(config.billing_start_day, 15)
    
    def test_config_data_json_serialization(self):
        """Test that ConfigData can be serialized to JSON."""
        from src.shared.data_models import ConfigData
        
        config = ConfigData(
            total_monthly_sessions=75,
            local_timezone="UTC",
            billing_start_day=10
        )
        
        json_data = config.to_json()
        self.assertIsInstance(json_data, str)
        
        # Test deserialization
        restored_config = ConfigData.from_json(json_data)
        self.assertEqual(restored_config.total_monthly_sessions, 75)
        self.assertEqual(restored_config.local_timezone, "UTC")
        self.assertEqual(restored_config.billing_start_day, 10)


class TestErrorStatus(unittest.TestCase):
    """Test cases for ErrorStatus model."""
    
    def test_error_status_creation(self):
        """Test that ErrorStatus can track ccusage errors."""
        from src.shared.data_models import ErrorStatus
        
        error = ErrorStatus(
            has_error=True,
            error_message="ccusage command not found",
            error_code=127,
            last_successful_update=datetime(2024, 1, 15, 10, 0, 0, tzinfo=ZoneInfo("UTC")),
            consecutive_failures=3
        )
        
        self.assertTrue(error.has_error)
        self.assertEqual(error.error_message, "ccusage command not found")
        self.assertEqual(error.error_code, 127)
        self.assertEqual(error.consecutive_failures, 3)
    
    def test_error_status_no_error(self):
        """Test that ErrorStatus can represent successful state."""
        from src.shared.data_models import ErrorStatus
        
        error = ErrorStatus(
            has_error=False,
            error_message=None,
            error_code=None,
            last_successful_update=datetime.now(ZoneInfo("UTC")),
            consecutive_failures=0
        )
        
        self.assertFalse(error.has_error)
        self.assertIsNone(error.error_message)
        self.assertIsNone(error.error_code)
        self.assertEqual(error.consecutive_failures, 0)


if __name__ == '__main__':
    unittest.main()