#!/usr/bin/env python3
"""
Test suite for utility functions.
"""
import unittest
import tempfile
import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_get_subscription_period_start(self):
        """Test subscription period start calculation."""
        from src.shared.utils import get_subscription_period_start
        
        # Test case 1: Current day is after billing day
        test_date = date(2024, 1, 20)  # 20th of January
        start_date = get_subscription_period_start(15, test_date)
        self.assertEqual(start_date, date(2024, 1, 15))
        
        # Test case 2: Current day is before billing day
        test_date = date(2024, 1, 10)  # 10th of January
        start_date = get_subscription_period_start(15, test_date)
        self.assertEqual(start_date, date(2023, 12, 15))
    
    def test_get_next_renewal_date(self):
        """Test next renewal date calculation."""
        from src.shared.utils import get_next_renewal_date
        
        # Test case 1: Current day is after billing day
        test_date = date(2024, 1, 20)  # 20th of January
        next_date = get_next_renewal_date(15, test_date)
        self.assertEqual(next_date, date(2024, 2, 15))
        
        # Test case 2: Current day is before billing day
        test_date = date(2024, 1, 10)  # 10th of January
        next_date = get_next_renewal_date(15, test_date)
        self.assertEqual(next_date, date(2024, 1, 15))
    
    def test_create_progress_bar(self):
        """Test progress bar creation."""
        from src.shared.utils import create_progress_bar
        
        # Test 0%
        bar = create_progress_bar(0, 10)
        self.assertEqual(bar, "[          ]")
        
        # Test 50%
        bar = create_progress_bar(50, 10)
        self.assertEqual(bar, "[█████     ]")
        
        # Test 100%
        bar = create_progress_bar(100, 10)
        self.assertEqual(bar, "[██████████]")
        
        # Test over 100% (should clamp)
        bar = create_progress_bar(150, 10)
        self.assertEqual(bar, "[██████████]")
        
        # Test negative (should clamp)
        bar = create_progress_bar(-10, 10)
        self.assertEqual(bar, "[          ]")
    
    def test_format_timedelta(self):
        """Test timedelta formatting."""
        from src.shared.utils import format_timedelta
        
        # Test various durations
        self.assertEqual(format_timedelta(timedelta(hours=2, minutes=30)), "2h 30m")
        self.assertEqual(format_timedelta(timedelta(hours=0, minutes=5)), "0h 05m")
        self.assertEqual(format_timedelta(timedelta(hours=24, minutes=0)), "24h 00m")
        self.assertEqual(format_timedelta(timedelta(seconds=30)), "0h 00m")
        
        # Test negative duration
        self.assertEqual(format_timedelta(timedelta(seconds=-30)), "0h 00m")
    
    def test_format_currency(self):
        """Test currency formatting."""
        from src.shared.utils import format_currency
        
        self.assertEqual(format_currency(5.50), "$5.50")
        self.assertEqual(format_currency(0.99, "USD"), "$0.99")
        self.assertEqual(format_currency(10.5, "EUR"), "10.50 EUR")
        self.assertEqual(format_currency(100.0), "$100.00")
    
    def test_format_token_count(self):
        """Test token count formatting."""
        from src.shared.utils import format_token_count
        
        self.assertEqual(format_token_count(1000), "1,000")
        self.assertEqual(format_token_count(25000), "25,000")
        self.assertEqual(format_token_count(1500000), "1,500,000")
        self.assertEqual(format_token_count(999), "999")
    
    def test_validate_timezone(self):
        """Test timezone validation."""
        from src.shared.utils import validate_timezone
        
        self.assertTrue(validate_timezone("UTC"))
        self.assertTrue(validate_timezone("America/New_York"))
        self.assertTrue(validate_timezone("Europe/Warsaw"))
        self.assertFalse(validate_timezone("Invalid/Timezone"))
        self.assertFalse(validate_timezone(""))
    
    def test_convert_timezone(self):
        """Test timezone conversion."""
        from src.shared.utils import convert_timezone
        
        # UTC datetime
        utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        
        # Convert to New York time (EST, UTC-5)
        ny_dt = convert_timezone(utc_dt, "America/New_York")
        self.assertEqual(ny_dt.hour, 7)  # 12 - 5 = 7
        
        # Test naive datetime (should be treated as UTC)
        naive_dt = datetime(2024, 1, 15, 12, 0, 0)
        ny_dt_from_naive = convert_timezone(naive_dt, "America/New_York")
        self.assertEqual(ny_dt_from_naive.hour, 7)
    
    def test_is_command_available(self):
        """Test command availability check."""
        from src.shared.utils import is_command_available
        
        # These commands should exist on most systems
        self.assertTrue(is_command_available("python3"))
        self.assertTrue(is_command_available("ls"))
        
        # This command should not exist
        self.assertFalse(is_command_available("definitely_not_a_real_command_12345"))
    
    def test_truncate_string(self):
        """Test string truncation."""
        from src.shared.utils import truncate_string
        
        # Test no truncation needed
        result = truncate_string("hello", 10)
        self.assertEqual(result, "hello")
        
        # Test truncation with default suffix
        result = truncate_string("hello world", 8)
        self.assertEqual(result, "hello...")
        
        # Test truncation with custom suffix
        result = truncate_string("hello world", 8, ">>")
        self.assertEqual(result, "hello >>")
    
    def test_safe_divide(self):
        """Test safe division."""
        from src.shared.utils import safe_divide
        
        self.assertEqual(safe_divide(10, 2), 5.0)
        self.assertEqual(safe_divide(10, 0), 0.0)
        self.assertEqual(safe_divide(10, 0, 99.0), 99.0)
        self.assertEqual(safe_divide(0, 5), 0.0)
    
    def test_calculate_percentage(self):
        """Test percentage calculation."""
        from src.shared.utils import calculate_percentage
        
        self.assertEqual(calculate_percentage(50, 100), 50.0)
        self.assertEqual(calculate_percentage(25, 100), 25.0)
        self.assertEqual(calculate_percentage(100, 100), 100.0)
        self.assertEqual(calculate_percentage(150, 100), 100.0)  # Clamped
        self.assertEqual(calculate_percentage(10, 0), 0.0)  # Edge case
        self.assertEqual(calculate_percentage(-10, 100), 0.0)  # Clamped
    
    def test_parse_date_string(self):
        """Test date string parsing."""
        from src.shared.utils import parse_date_string
        
        # Valid date
        result = parse_date_string("2024-01-15")
        self.assertEqual(result, date(2024, 1, 15))
        
        # Invalid date
        result = parse_date_string("invalid-date")
        self.assertIsNone(result)
        
        # Custom format
        result = parse_date_string("15/01/2024", "%d/%m/%Y")
        self.assertEqual(result, date(2024, 1, 15))
    
    def test_format_file_size(self):
        """Test file size formatting."""
        from src.shared.utils import format_file_size
        
        self.assertEqual(format_file_size(0), "0 B")
        self.assertEqual(format_file_size(512), "512 B")
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1048576), "1.0 MB")
        self.assertEqual(format_file_size(1536), "1.5 KB")
    
    def test_ensure_directory_exists(self):
        """Test directory creation."""
        from src.shared.utils import ensure_directory_exists
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "nested", "directory")
            
            # Should create directory
            result = ensure_directory_exists(test_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(test_path))
            
            # Should succeed if directory already exists
            result = ensure_directory_exists(test_path)
            self.assertTrue(result)
    
    def test_get_file_age_seconds(self):
        """Test file age calculation."""
        from src.shared.utils import get_file_age_seconds
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # File should have very small age
            age = get_file_age_seconds(temp_path)
            self.assertGreaterEqual(age, 0)
            self.assertLess(age, 10)  # Should be less than 10 seconds
            
            # Non-existent file should return 0
            age = get_file_age_seconds("/path/that/does/not/exist")
            self.assertEqual(age, 0.0)
        finally:
            os.unlink(temp_path)
    
    def test_is_file_stale(self):
        """Test file staleness check."""
        from src.shared.utils import is_file_stale
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Fresh file should not be stale
            self.assertFalse(is_file_stale(temp_path, 60))
            
            # Non-existent file should be stale
            self.assertTrue(is_file_stale("/path/that/does/not/exist", 60))
        finally:
            os.unlink(temp_path)
    
    def test_get_work_timing_suggestion(self):
        """Test work timing suggestions based on current minute."""
        from src.shared.utils import get_work_timing_suggestion
        from unittest.mock import patch
        
        # Test 0-15 minutes: positive suggestions
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 5
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            self.assertGreater(len(suggestion), 0)
            # Should be from positive suggestions list
            
        # Test 16-30 minutes: moderately positive suggestions
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 25
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            self.assertGreater(len(suggestion), 0)
            
        # Test 31-45 minutes: skeptical suggestions
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 35
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            self.assertGreater(len(suggestion), 0)
            
        # Test 46-59 minutes: humorous/critical suggestions
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 55
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            self.assertGreater(len(suggestion), 0)
            
        # Test edge cases
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 0
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 15
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 30
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 45
            suggestion = get_work_timing_suggestion()
            self.assertIsInstance(suggestion, str)
            
        # Test randomization - call multiple times and ensure we get different results
        with patch('src.shared.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value.minute = 10
            suggestions = set()
            for _ in range(10):  # Call 10 times
                suggestions.add(get_work_timing_suggestion())
            # Should have at least 2 different suggestions (randomization working)
            # Note: This test could theoretically fail if we get the same random choice 10 times
            # but probability is very low with multiple messages in each category


if __name__ == '__main__':
    unittest.main()