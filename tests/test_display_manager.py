#!/usr/bin/env python3

import unittest
import io
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.client.display_manager import DisplayManager
from src.shared.data_models import MonitoringData, SessionData, ActivitySessionData


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
        
        # Create monitoring data with activity sessions
        self.activity_sessions_sample = [
            ActivitySessionData(
                project_name="test_project_1",
                session_id="test-activity-1",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                status="ACTIVE",
                event_type="notification"
            ),
            ActivitySessionData(
                project_name="test_project_2",
                session_id="test-activity-2",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=10),
                status="WAITING_FOR_USER",
                event_type="stop"
            )
        ]
        
        self.monitoring_data_with_activity = MonitoringData(
            current_sessions=[self.active_session],
            total_sessions_this_month=1,
            total_cost_this_month=5.25,
            max_tokens_per_session=5000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15),
            activity_sessions=self.activity_sessions_sample
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

    def test_render_activity_sessions_with_icons(self):
        """Test rendering activity sessions with status icons (RED test)."""
        # Create sample activity sessions with different statuses
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="active-session-1",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                status="ACTIVE",
                event_type="notification"
            ),
            ActivitySessionData(
                project_name="test_project",
                session_id="waiting-session-2",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
                status="WAITING_FOR_USER",
                event_type="stop"
            ),
            ActivitySessionData(
                project_name="test_project",
                session_id="idle-session-3",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=15),
                status="IDLE",
                event_type="stop"
            ),
            ActivitySessionData(
                project_name="test_project",
                session_id="inactive-session-4",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=45),
                status="INACTIVE",
                event_type="stop"
            )
        ]
        
        # Test rendering with icons for each status
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Check for activity sessions section header
            self.assertIn("CLAUDE CODE ACTIVITY", output)
            
            # Check for status icons and session IDs
            self.assertIn("🔵", output)  # ACTIVE icon
            self.assertIn("⏳", output)  # WAITING_FOR_USER icon
            self.assertIn("💤", output)  # IDLE icon
            self.assertIn("⛔", output)  # INACTIVE icon
            
            # Check for project names (truncated for display)
            self.assertIn("test_project", output)
            self.assertIn("ACTIVE", output)
            self.assertIn("WAITING_FOR_USER", output)
            self.assertIn("IDLE", output)
            self.assertIn("INACTIVE", output)

    def test_render_activity_sessions_empty_list(self):
        """Test rendering activity sessions with empty list."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions([])
            output = fake_out.getvalue()
            
            # Should show a message about no activity sessions
            self.assertIn("No activity sessions", output)

    def test_render_activity_sessions_single_active(self):
        """Test rendering with only one active session."""
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="single-active",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=2),
                status="ACTIVE",
                event_type="notification"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Check for header and single session
            self.assertIn("CLAUDE CODE ACTIVITY", output)
            self.assertIn("🔵", output)  # ACTIVE icon
            self.assertIn("test_project", output)  # Project name
            self.assertIn("ACTIVE", output)

    def test_render_activity_sessions_configuration_usage(self):
        """Test that activity sessions use configuration properly."""
        # Modify configuration for testing
        original_config = self.display_manager.activity_config.copy()
        self.display_manager.activity_config["status_icons"]["ACTIVE"] = "🟢"
        self.display_manager.activity_config["max_project_name_length"] = 5
        self.display_manager.activity_config["show_timestamps"] = False
        
        activity_sessions = [
            ActivitySessionData(
                project_name="very-long-project-name",
                session_id="test-session-id",
                start_time=datetime.now(timezone.utc),
                status="ACTIVE",
                event_type="notification"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Check for modified icon
            self.assertIn("🟢", output)  # Custom ACTIVE icon
            
            # Check for project name truncation at 5 chars
            self.assertIn("very-...", output)
            
            # Check that timestamp is not shown
            timestamp_pattern = r'\(\d{2}:\d{2}:\d{2}\)'
            import re
            self.assertIsNone(re.search(timestamp_pattern, output))
        
        # Restore original configuration
        self.display_manager.activity_config = original_config

    def test_render_activity_sessions_mixed_statuses(self):
        """Test rendering with mixed session statuses."""
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="session-1",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
                status="ACTIVE",
                event_type="notification"
            ),
            ActivitySessionData(
                project_name="test_project",
                session_id="session-2", 
                start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                status="WAITING_FOR_USER",
                event_type="stop"
            ),
            ActivitySessionData(
                project_name="test_project",
                session_id="session-3",
                start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                status="INACTIVE",
                event_type="stop"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Check for header
            self.assertIn("CLAUDE CODE ACTIVITY", output)
            
            # Check for different icons
            self.assertIn("🔵", output)  # ACTIVE
            self.assertIn("⏳", output)  # WAITING_FOR_USER
            self.assertIn("⛔", output)  # INACTIVE
            
            # Check for all sessions with project names
            self.assertIn("test_project", output)
            self.assertIn("ACTIVE", output)
            self.assertIn("WAITING_FOR_USER", output)
            self.assertIn("INACTIVE", output)

    def test_render_activity_sessions_unknown_status(self):
        """Test rendering with unknown status gets fallback icon."""
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="unknown-status",
                start_time=datetime.now(timezone.utc),
                status="UNKNOWN_STATUS",
                event_type="unknown"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Check for fallback icon
            self.assertIn("❓", output)
            self.assertIn("UNKNOWN_STATUS", output)

    def test_render_full_display_includes_activity_sessions(self):
        """Test that main display includes activity sessions section (RED test)."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager.render_full_display(self.monitoring_data_with_activity)
            output = fake_out.getvalue()
            
            # Check for main header
            self.assertIn("CLAUDE SESSION MONITOR", output)
            
            # Check for activity sessions section
            self.assertIn("CLAUDE CODE ACTIVITY", output)
            
            # Check for activity session data
            self.assertIn("🔵", output)  # ACTIVE icon
            self.assertIn("⏳", output)  # WAITING_FOR_USER icon
            self.assertIn("test_project", output)  # Project names
            
            # Check for traditional session data
            self.assertIn("Token Usage:", output)
            self.assertIn("Time to Reset:", output)

    def test_render_full_display_without_activity_sessions(self):
        """Test that main display works when no activity sessions (RED test)."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager.render_full_display(self.monitoring_data_active)
            output = fake_out.getvalue()
            
            # Check for main header
            self.assertIn("CLAUDE SESSION MONITOR", output)
            
            # Should show "No activity sessions" message
            self.assertIn("No activity sessions", output)
            
            # Check for traditional session data
            self.assertIn("Token Usage:", output)
            self.assertIn("Time to Reset:", output)

    def test_render_full_display_activity_sessions_none(self):
        """Test that main display handles None activity_sessions gracefully (RED test)."""
        # Ensure activity_sessions is None (default)
        self.monitoring_data_active.activity_sessions = None
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager.render_full_display(self.monitoring_data_active)
            output = fake_out.getvalue()
            
            # Check for main header
            self.assertIn("CLAUDE SESSION MONITOR", output)
            
            # Should show "No activity sessions" message
            self.assertIn("No activity sessions", output)

    def test_render_activity_sessions_disabled(self):
        """Test that activity sessions can be disabled via configuration."""
        # Disable activity sessions
        self.display_manager.activity_config["enabled"] = False
        
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="test-session",
                start_time=datetime.now(timezone.utc),
                status="ACTIVE",
                event_type="notification"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Should not display anything when disabled
            self.assertEqual(output, "")

    def test_render_activity_sessions_minimal_verbosity(self):
        """Test minimal verbosity display mode."""
        # Set minimal verbosity
        self.display_manager.activity_config["verbosity"] = "minimal"
        
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="session-1",
                start_time=datetime.now(timezone.utc),
                status="ACTIVE",
                event_type="notification"
            ),
            ActivitySessionData(
                project_name="test_project",
                session_id="session-2",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                status="WAITING_FOR_USER",
                event_type="stop"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Check for compact header
            self.assertIn("Activity: 2 sessions", output)
            
            # Check for compact status display  
            self.assertIn("🔵", output)
            self.assertIn("ACTIVE", output)
            self.assertIn("⏳", output)
            self.assertIn("WAITING_FOR_USER", output)
            
            # Should not have full header in minimal mode
            self.assertNotIn("CLAUDE CODE ACTIVITY", output)

    def test_render_activity_sessions_verbose_mode(self):
        """Test verbose display mode with detailed information."""
        # Set verbose mode
        self.display_manager.activity_config["verbosity"] = "verbose"
        
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="verbose-session",
                start_time=datetime.now(timezone.utc),
                status="ACTIVE",
                event_type="notification",
                metadata={"tool": "test", "user": "claude"}
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Check for verbose elements
            self.assertIn("CLAUDE CODE ACTIVITY", output)
            self.assertIn("Status:", output)
            self.assertIn("ACTIVE", output)
            self.assertIn("[notification]", output)
            self.assertIn("Metadata: tool=test, user=claude", output)

    def test_render_activity_sessions_filter_inactive(self):
        """Test filtering out inactive sessions."""
        # Configure to hide inactive sessions
        self.display_manager.activity_config["show_inactive_sessions"] = False
        
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="active-session",
                start_time=datetime.now(timezone.utc),
                status="ACTIVE",
                event_type="notification"
            ),
            ActivitySessionData(
                project_name="test_project",
                session_id="inactive-session",
                start_time=datetime.now(timezone.utc) - timedelta(hours=2),
                status="INACTIVE",
                event_type="stop"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Should show active but not inactive
            self.assertIn("test_project", output)  # Project name
            self.assertIn("ACTIVE", output)  # Active status
            self.assertNotIn("INACTIVE", output)  # Should not appear
            self.assertIn("🔵", output)  # ACTIVE icon
            self.assertNotIn("⚫", output)  # INACTIVE icon

    def test_render_activity_sessions_max_limit(self):
        """Test limiting the number of displayed sessions."""
        # Set low limit
        self.display_manager.activity_config["max_sessions_displayed"] = 2
        
        # Create 4 sessions
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id=f"session-{i}",
                start_time=datetime.now(timezone.utc) - timedelta(minutes=i),
                status="ACTIVE",
                event_type="notification"
            )
            for i in range(4)
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Should only show 2 most recent sessions (limited by max_sessions_displayed)
            # Count the number of project names displayed
            project_count = output.count("test_project")
            self.assertEqual(project_count, 2)  # Should only show 2 sessions

    def test_render_activity_sessions_no_timestamps(self):
        """Test disabling timestamps in display."""
        # Disable timestamps
        self.display_manager.activity_config["show_timestamps"] = False
        
        activity_sessions = [
            ActivitySessionData(
                project_name="test_project",
                session_id="no-timestamp",
                start_time=datetime.now(timezone.utc),
                status="ACTIVE",
                event_type="notification"
            )
        ]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            self.display_manager._render_activity_sessions(activity_sessions)
            output = fake_out.getvalue()
            
            # Should not contain timestamp pattern
            timestamp_pattern = r'\(\d{2}:\d{2}:\d{2}\)'
            import re
            self.assertIsNone(re.search(timestamp_pattern, output))
            
            # But should still show session
            self.assertIn("test_project", output)  # Project name
            self.assertIn("ACTIVE", output)

    def test_screen_clear_on_transition(self):
        """Test that screen is cleared when transitioning between active and waiting states (RED test)."""
        # Create a display manager with mock print output
        display_manager = DisplayManager()
        
        # Mock the clear_screen and move_to_top methods to track calls
        with patch.object(display_manager, 'clear_screen') as mock_clear, \
             patch.object(display_manager, 'move_to_top') as mock_move, \
             patch('sys.stdout', new=io.StringIO()):
            
            # First render: active session (should clear screen on first run)
            display_manager.render_full_display(self.monitoring_data_active)
            
            # Verify initial clear was called
            self.assertEqual(mock_clear.call_count, 1)
            self.assertEqual(mock_move.call_count, 0)
            
            # Reset mock call counts
            mock_clear.reset_mock()
            mock_move.reset_mock()
            
            # Second render: same active session (should only move to top)
            display_manager.render_full_display(self.monitoring_data_active)
            
            # Should only move to top, not clear screen
            self.assertEqual(mock_clear.call_count, 0)
            self.assertEqual(mock_move.call_count, 1)
            
            # Reset mock call counts
            mock_clear.reset_mock()
            mock_move.reset_mock()
            
            # Third render: transition to waiting state (should clear screen)
            display_manager.render_full_display(self.monitoring_data_waiting)
            
            # Should clear screen due to state transition, not just move to top
            self.assertEqual(mock_clear.call_count, 1)
            self.assertEqual(mock_move.call_count, 0)
            
            # Reset mock call counts
            mock_clear.reset_mock()
            mock_move.reset_mock()
            
            # Fourth render: same waiting state (should only move to top)
            display_manager.render_full_display(self.monitoring_data_waiting)
            
            # Should only move to top, not clear screen
            self.assertEqual(mock_clear.call_count, 0)
            self.assertEqual(mock_move.call_count, 1)
            
            # Reset mock call counts
            mock_clear.reset_mock()
            mock_move.reset_mock()
            
            # Fifth render: transition back to active state (should clear screen)
            display_manager.render_full_display(self.monitoring_data_active)
            
            # Should clear screen due to state transition, not just move to top
            self.assertEqual(mock_clear.call_count, 1)
            self.assertEqual(mock_move.call_count, 0)

    def test_timing_display_integration(self):
        """Test that timing suggestions are displayed in waiting state."""
        display_manager = DisplayManager()
        
        # Create monitoring data with no active sessions (waiting state)
        monitoring_data_waiting = MonitoringData(
            current_sessions=[self.completed_session],  # Only completed sessions
            total_sessions_this_month=1,
            total_cost_this_month=3.15,
            max_tokens_per_session=3000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
        )
        
        # Capture stdout to check if timing suggestions are displayed
        with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
            display_manager.render_waiting_display(monitoring_data_waiting)
            output = mock_stdout.getvalue()
            
            # Check that waiting message is displayed
            self.assertIn("Waiting for a new session to start", output)
            
            # Check that timing suggestion is displayed
            self.assertIn("Timing suggestion:", output)
            
            # Check that the suggestion is not empty
            lines = output.split('\n')
            timing_lines = [line for line in lines if 'Timing suggestion:' in line]
            self.assertEqual(len(timing_lines), 1)
            
            # Extract the suggestion text
            timing_line = timing_lines[0]
            self.assertGreater(len(timing_line), len("Timing suggestion:"))
            
    def test_timing_display_different_times(self):
        """Test timing suggestions for different time ranges."""
        display_manager = DisplayManager()
        
        # Create monitoring data for waiting state
        monitoring_data_waiting = MonitoringData(
            current_sessions=[self.completed_session],
            total_sessions_this_month=1,
            total_cost_this_month=3.15,
            max_tokens_per_session=3000,
            last_update=datetime.now(timezone.utc),
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=15),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=15)
        )
        
        # Test different time ranges
        test_times = [5, 25, 35, 55]  # Representative minutes from each range
        
        for test_minute in test_times:
            with patch('src.shared.utils.datetime') as mock_datetime:
                mock_datetime.now.return_value.minute = test_minute
                
                with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                    display_manager.render_waiting_display(monitoring_data_waiting)
                    output = mock_stdout.getvalue()
                    
                    # Check timing suggestion is present
                    self.assertIn("Timing suggestion:", output)
                    
                    # Check suggestion is not empty
                    lines = output.split('\n')
                    timing_lines = [line for line in lines if 'Timing suggestion:' in line]
                    self.assertEqual(len(timing_lines), 1)


if __name__ == '__main__':
    unittest.main()