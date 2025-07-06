#!/usr/bin/env python3
"""
Test suite for ActivitySessionData model.
Following TDD approach - RED phase implementation.
"""
import unittest
import json
from datetime import datetime
from zoneinfo import ZoneInfo


class TestActivitySessionData(unittest.TestCase):
    """Test cases for ActivitySessionData model."""
    
    def test_activity_session_data_creation(self):
        """Test basic creation of ActivitySessionData with required fields."""
        from src.shared.data_models import ActivitySessionData
        
        # Create activity session data instance
        activity_session = ActivitySessionData(
            session_id="claude_session_456",
            start_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=ZoneInfo("UTC")),
            status="ACTIVE"
        )
        
        # Verify basic fields
        self.assertEqual(activity_session.session_id, "claude_session_456")
        self.assertEqual(activity_session.status, "ACTIVE")
        self.assertIsInstance(activity_session.start_time, datetime)
    
    def test_activity_session_data_serialization(self):
        """Test that ActivitySessionData can be serialized to JSON and back."""
        from src.shared.data_models import ActivitySessionData
        
        activity_session = ActivitySessionData(
            session_id="claude_session_789",
            start_time=datetime(2024, 1, 15, 14, 20, 0, tzinfo=ZoneInfo("UTC")),
            status="WAITING",
            event_type="notification",
            metadata={"tool_name": "bash", "command": "ls"}
        )
        
        # Test serialization
        json_data = activity_session.to_json()
        self.assertIsInstance(json_data, str)
        
        # Test that JSON is valid
        parsed = json.loads(json_data)
        self.assertIn("session_id", parsed)
        self.assertIn("start_time", parsed)
        self.assertIn("status", parsed)
        
        # Test deserialization
        restored_session = ActivitySessionData.from_json(json_data)
        self.assertEqual(restored_session.session_id, activity_session.session_id)
        self.assertEqual(restored_session.status, activity_session.status)
        self.assertEqual(restored_session.event_type, activity_session.event_type)
    
    def test_activity_session_data_validation(self):
        """Test validation of ActivitySessionData fields."""
        from src.shared.data_models import ActivitySessionData, ValidationError
        
        # Valid session should pass validation
        valid_session = ActivitySessionData(
            session_id="valid_session",
            start_time=datetime.now(ZoneInfo("UTC")),
            status="ACTIVE"
        )
        self.assertTrue(valid_session.validate_schema())
        
        # Invalid session_id should raise ValidationError
        with self.assertRaises(ValidationError):
            invalid_session = ActivitySessionData(
                session_id="",  # Empty session_id
                start_time=datetime.now(ZoneInfo("UTC")),
                status="ACTIVE"
            )
            invalid_session.validate_schema()
    
    def test_activity_session_status_enum(self):
        """Test that ActivitySessionData uses valid status values."""
        from src.shared.data_models import ActivitySessionData, ActivitySessionStatus
        
        # Test enum values
        self.assertEqual(ActivitySessionStatus.ACTIVE.value, "ACTIVE")
        self.assertEqual(ActivitySessionStatus.WAITING.value, "WAITING")
        self.assertEqual(ActivitySessionStatus.STOPPED.value, "STOPPED")
        
        # Test valid session with enum
        session = ActivitySessionData(
            session_id="enum_test",
            start_time=datetime.now(ZoneInfo("UTC")),
            status=ActivitySessionStatus.ACTIVE.value
        )
        self.assertEqual(session.status, "ACTIVE")


if __name__ == '__main__':
    unittest.main()