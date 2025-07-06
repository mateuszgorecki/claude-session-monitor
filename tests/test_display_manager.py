#!/usr/bin/env python3

import unittest
import io
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.client.display_manager import DisplayManager
from src.shared.data_models import MonitoringData, SessionData


class TestDisplayManager(unittest.TestCase):
    """Test suite for DisplayManager class following TDD approach."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create sample session data
        self.active_session = SessionData(
            session_id="test-session-active",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
            end_time=datetime.now(timezone.utc) + timedelta(minutes=30),
            total_tokens=5000,
            input_tokens=2000,
            output_tokens=3000,
            cost_usd=5.25,
            is_active=True
        )
        
        self.completed_session = SessionData(
            session_id="test-session-completed",
            start_time=datetime.now(timezone.utc) - timedelta(hours=2),
            end_time=datetime.now(timezone.utc) - timedelta(hours=1),
            total_tokens=3000,
            input_tokens=1200,
            output_tokens=1800,
            cost_usd=3.15,
            is_active=False
        )
        
        # Create monitoring data with active session
        self.monitoring_data_active = MonitoringData(
            current_sessions=[self.active_session, self.completed_session],
            total_sessions_this_month=2,
            total_cost_this_month=8.40,
            max_tokens_per_session=5000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
        )
        
        # Create monitoring data without active session
        self.monitoring_data_waiting = MonitoringData(
            current_sessions=[self.completed_session],
            total_sessions_this_month=1,
            total_cost_this_month=3.15,
            max_tokens_per_session=3000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
        )
        
        self.display_manager = DisplayManager()

    def test_create_progress_bar(self):
        """Test progress bar creation with different percentages."""
        # Test 0%
        bar_0 = self.display_manager.create_progress_bar(0.0)
        self.assertEqual(bar_0, "[" + " " * 40 + "]")
        
        # Test 50%
        bar_50 = self.display_manager.create_progress_bar(50.0)
        expected_50 = "[" + "█" * 20 + " " * 20 + "]"
        self.assertEqual(bar_50, expected_50)
        
        # Test 100%
        bar_100 = self.display_manager.create_progress_bar(100.0)
        self.assertEqual(bar_100, "[" + "█" * 40 + "]")
        
        # Test custom width
        bar_custom = self.display_manager.create_progress_bar(25.0, width=20)
        expected_custom = "[" + "█" * 5 + " " * 15 + "]"
        self.assertEqual(bar_custom, expected_custom)

    def test_format_timedelta(self):
        """Test time delta formatting."""
        # Test hours and minutes
        td_1h30m = timedelta(hours=1, minutes=30)
        self.assertEqual(self.display_manager.format_timedelta(td_1h30m), "1h 30m")
        
        # Test just minutes
        td_45m = timedelta(minutes=45)
        self.assertEqual(self.display_manager.format_timedelta(td_45m), "0h 45m")
        
        # Test zero time
        td_0 = timedelta(seconds=0)
        self.assertEqual(self.display_manager.format_timedelta(td_0), "0h 00m")
        
        # Test with seconds (should be ignored)
        td_complex = timedelta(hours=2, minutes=15, seconds=45)
        self.assertEqual(self.display_manager.format_timedelta(td_complex), "2h 15m")

    def test_clear_screen(self):
        """Test screen clearing functionality."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager.clear_screen()
            output = fake_out.getvalue()
            # Should contain ANSI escape sequences for clearing screen
            self.assertIn("\033[H\033[J\033[?25l", output)

    def test_calculate_token_usage_percentage(self):
        """Test token usage percentage calculation."""
        # Test normal case
        current_tokens = 2500
        max_tokens = 10000
        percentage = self.display_manager.calculate_token_usage_percentage(current_tokens, max_tokens)
        self.assertEqual(percentage, 25.0)
        
        # Test edge case - zero max tokens
        percentage_zero = self.display_manager.calculate_token_usage_percentage(1000, 0)
        self.assertEqual(percentage_zero, 0.0)
        
        # Test edge case - current > max
        percentage_over = self.display_manager.calculate_token_usage_percentage(15000, 10000)
        self.assertEqual(percentage_over, 150.0)

    def test_calculate_time_progress_percentage(self):
        """Test time progress percentage calculation."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc) + timedelta(hours=1)
        current_time = datetime.now(timezone.utc)
        
        percentage = self.display_manager.calculate_time_progress_percentage(
            start_time, end_time, current_time
        )
        
        # Should be around 50% (halfway through 2-hour session)
        self.assertAlmostEqual(percentage, 50.0, delta=5.0)

    def test_find_active_session(self):
        """Test finding active session from monitoring data."""
        # Test with active session
        active = self.display_manager.find_active_session(self.monitoring_data_active)
        self.assertIsNotNone(active)
        self.assertTrue(active.is_active)
        self.assertEqual(active.session_id, "test-session-active")
        
        # Test without active session
        active_none = self.display_manager.find_active_session(self.monitoring_data_waiting)
        self.assertIsNone(active_none)

    def test_calculate_session_stats(self):
        """Test session statistics calculation."""
        total_monthly_sessions = 50
        current_sessions = 15
        days_in_period = 30
        days_remaining = 15
        
        stats = self.display_manager.calculate_session_stats(
            total_monthly_sessions, current_sessions, days_in_period, days_remaining
        )
        
        self.assertEqual(stats['sessions_used'], 15)
        self.assertEqual(stats['sessions_left'], 35)
        # 35 sessions remaining / 15 days remaining = 2.33 sessions per day
        self.assertAlmostEqual(stats['avg_sessions_per_day'], 35/15, places=2)

    def test_render_active_session_display(self):
        """Test rendering display for active session."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager.render_active_session_display(
                self.monitoring_data_active, self.active_session
            )
            output = fake_out.getvalue()
            
            # Check for key elements in output
            self.assertIn("Token Usage:", output)
            self.assertIn("Time to Reset:", output)
            self.assertIn("Tokens:", output)
            self.assertIn("Session Cost:", output)
            self.assertIn("█", output)  # Progress bar characters

    def test_render_waiting_display(self):
        """Test rendering display when waiting for session."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager.render_waiting_display(self.monitoring_data_waiting)
            output = fake_out.getvalue()
            
            # Check for waiting message
            self.assertIn("Waiting for a new session to start", output)
            self.assertIn("Saved max tokens:", output)

    def test_render_footer(self):
        """Test rendering footer with session stats."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            current_time = datetime.now()
            session_stats = {
                'sessions_used': 15,
                'sessions_left': 35,
                'avg_sessions_per_day': 1.2
            }
            days_remaining = 20
            total_cost = 125.75
            
            self.display_manager.render_footer(
                current_time, session_stats, days_remaining, total_cost
            )
            output = fake_out.getvalue()
            
            # Check for footer elements
            self.assertIn("=" * 60, output)
            self.assertIn("Sessions:", output)
            self.assertIn("15 used, 35 left", output)
            self.assertIn("$125.75", output)
            self.assertIn("Ctrl+C exit", output)
            self.assertIn("Server:", output)


if __name__ == '__main__':
    unittest.main()