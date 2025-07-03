#!/usr/bin/env python3
"""
Test suite for JSON Schema validation in data models.
"""
import unittest
import json
from datetime import datetime
from zoneinfo import ZoneInfo


class TestJSONSchemaValidation(unittest.TestCase):
    """Test cases for JSON Schema validation."""
    
    def test_session_data_schema_validation_valid(self):
        """Test that valid SessionData passes schema validation."""
        from src.shared.data_models import SessionData
        
        # Valid session data
        session = SessionData(
            session_id="valid_session_123",
            start_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC")),
            end_time=datetime(2024, 1, 15, 11, 45, 0, tzinfo=ZoneInfo("UTC")),
            total_tokens=25000,
            input_tokens=5000,
            output_tokens=20000,
            cost_usd=0.85,
            is_active=False
        )
        
        # Should not raise any validation errors
        self.assertTrue(session.validate_schema())
    
    def test_session_data_schema_validation_invalid_tokens(self):
        """Test that invalid token values fail schema validation."""
        from src.shared.data_models import SessionData, ValidationError
        
        # Invalid: negative tokens
        with self.assertRaises(ValidationError):
            session = SessionData(
                session_id="invalid_session",
                start_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC")),
                end_time=datetime(2024, 1, 15, 11, 45, 0, tzinfo=ZoneInfo("UTC")),
                total_tokens=-1000,  # Invalid: negative
                input_tokens=5000,
                output_tokens=20000,
                cost_usd=0.85,
                is_active=False
            )
            session.validate_schema()
    
    def test_session_data_schema_validation_invalid_cost(self):
        """Test that invalid cost values fail schema validation."""
        from src.shared.data_models import SessionData, ValidationError
        
        # Invalid: negative cost
        with self.assertRaises(ValidationError):
            session = SessionData(
                session_id="invalid_cost_session",
                start_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC")),
                end_time=datetime(2024, 1, 15, 11, 45, 0, tzinfo=ZoneInfo("UTC")),
                total_tokens=25000,
                input_tokens=5000,
                output_tokens=20000,
                cost_usd=-0.85,  # Invalid: negative cost
                is_active=False
            )
            session.validate_schema()
    
    def test_session_data_schema_validation_token_consistency(self):
        """Test that token consistency is validated."""
        from src.shared.data_models import SessionData, ValidationError
        
        # Invalid: input + output != total
        with self.assertRaises(ValidationError):
            session = SessionData(
                session_id="inconsistent_tokens",
                start_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC")),
                end_time=datetime(2024, 1, 15, 11, 45, 0, tzinfo=ZoneInfo("UTC")),
                total_tokens=25000,
                input_tokens=5000,
                output_tokens=15000,  # 5000 + 15000 != 25000
                cost_usd=0.85,
                is_active=False
            )
            session.validate_schema()
    
    def test_monitoring_data_schema_validation(self):
        """Test that MonitoringData passes schema validation."""
        from src.shared.data_models import MonitoringData, SessionData
        
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
        
        # Should not raise any validation errors
        self.assertTrue(monitoring_data.validate_schema())
    
    def test_config_data_schema_validation(self):
        """Test that ConfigData passes schema validation."""
        from src.shared.data_models import ConfigData
        
        config = ConfigData(
            total_monthly_sessions=75,
            refresh_interval_seconds=2,
            ccusage_fetch_interval_seconds=15,
            time_remaining_alert_minutes=45,
            inactivity_alert_minutes=15,
            local_timezone="America/New_York",
            billing_start_day=10
        )
        
        # Should not raise any validation errors
        self.assertTrue(config.validate_schema())
    
    def test_config_data_schema_validation_invalid_intervals(self):
        """Test that invalid time intervals fail schema validation."""
        from src.shared.data_models import ConfigData, ValidationError
        
        # Invalid: zero refresh interval
        with self.assertRaises(ValidationError):
            config = ConfigData(
                total_monthly_sessions=75,
                refresh_interval_seconds=0,  # Invalid: must be positive
                ccusage_fetch_interval_seconds=15,
                time_remaining_alert_minutes=45,
                inactivity_alert_minutes=15,
                local_timezone="America/New_York",
                billing_start_day=10
            )
            config.validate_schema()
    
    def test_error_status_schema_validation(self):
        """Test that ErrorStatus passes schema validation."""
        from src.shared.data_models import ErrorStatus
        
        error = ErrorStatus(
            has_error=True,
            error_message="ccusage command not found",
            error_code=127,
            last_successful_update=datetime(2024, 1, 15, 10, 0, 0, tzinfo=ZoneInfo("UTC")),
            consecutive_failures=3
        )
        
        # Should not raise any validation errors
        self.assertTrue(error.validate_schema())
    
    def test_json_schema_validation_from_dict(self):
        """Test that schema validation works when creating from dict."""
        from src.shared.data_models import SessionData, ValidationError
        
        # Valid data
        valid_data = {
            "session_id": "test_session",
            "start_time": "2024-01-15T10:30:00+00:00",
            "end_time": "2024-01-15T11:45:00+00:00",
            "total_tokens": 25000,
            "input_tokens": 5000,
            "output_tokens": 20000,
            "cost_usd": 0.85,
            "is_active": False
        }
        
        session = SessionData.from_dict(valid_data)
        self.assertTrue(session.validate_schema())
        
        # Invalid data - negative tokens
        invalid_data = valid_data.copy()
        invalid_data["total_tokens"] = -1000
        
        with self.assertRaises(ValidationError):
            session = SessionData.from_dict(invalid_data)
            session.validate_schema()


if __name__ == '__main__':
    unittest.main()