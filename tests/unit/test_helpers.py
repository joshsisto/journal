"""Unit tests for helper functions."""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from helpers import get_feeling_emoji, format_time_since


class TestGetFeelingEmoji:
    """Test cases for the get_feeling_emoji function."""
    
    def test_valid_integer_inputs(self):
        """Test that valid integer inputs (1-10) return correct emojis."""
        expected_emojis = {
            1: "😭",
            2: "😢", 
            3: "😞",
            4: "😔",
            5: "😐",
            6: "🙂",
            7: "😊",
            8: "😄",
            9: "😁",
            10: "🤩"
        }
        
        for feeling_value, expected_emoji in expected_emojis.items():
            assert get_feeling_emoji(feeling_value) == expected_emoji

    def test_zero_value(self):
        """Test that zero input returns question mark emoji."""
        assert get_feeling_emoji(0) == "❓"

    def test_negative_values(self):
        """Test that negative values return question mark emoji."""
        assert get_feeling_emoji(-1) == "❓"
        assert get_feeling_emoji(-10) == "❓"

    def test_out_of_range_values(self):
        """Test that values outside 1-10 range return question mark emoji."""
        assert get_feeling_emoji(11) == "❓"
        assert get_feeling_emoji(1000000) == "❓"

    def test_float_inputs(self):
        """Test that float inputs are converted to integers."""
        # Float that truncates to valid value
        assert get_feeling_emoji(10.9) == "🤩"  # int(10.9) = 10
        assert get_feeling_emoji(5.1) == "😐"   # int(5.1) = 5
        
        # Float that truncates to invalid value
        assert get_feeling_emoji(0.9) == "❓"    # int(0.9) = 0

    def test_string_numeric_inputs(self):
        """Test that numeric strings are converted correctly."""
        assert get_feeling_emoji("5") == "😐"
        assert get_feeling_emoji("10") == "🤩"
        assert get_feeling_emoji("1") == "😭"

    def test_invalid_string_inputs(self):
        """Test that non-numeric strings return question mark emoji."""
        assert get_feeling_emoji("hello") == "❓"
        assert get_feeling_emoji("abc") == "❓"
        assert get_feeling_emoji("") == "❓"

    def test_none_input(self):
        """Test that None input returns question mark emoji."""
        assert get_feeling_emoji(None) == "❓"

    def test_invalid_type_inputs(self):
        """Test that invalid types return question mark emoji."""
        assert get_feeling_emoji([5]) == "❓"
        assert get_feeling_emoji({"value": 5}) == "❓"
        assert get_feeling_emoji(set([5])) == "❓"


class TestFormatTimeSince:
    """Test cases for the format_time_since function."""
    
    def test_none_input(self):
        """Test that None input returns 'your first entry'."""
        assert format_time_since(None) == "your first entry"

    def test_less_than_minute(self):
        """Test formatting for very short durations."""
        delta = timedelta(seconds=30)
        assert format_time_since(delta) == "less than a minute"

    def test_minutes_only(self):
        """Test formatting for minute-only durations."""
        delta = timedelta(minutes=5)
        assert format_time_since(delta) == "5 minutes"
        
        delta = timedelta(minutes=1)
        assert format_time_since(delta) == "1 minute"

    def test_hours_only(self):
        """Test formatting for hour-only durations."""
        delta = timedelta(hours=2)
        assert format_time_since(delta) == "2 hours"
        
        delta = timedelta(hours=1)
        assert format_time_since(delta) == "1 hour"

    def test_hours_and_minutes(self):
        """Test formatting for hour and minute combinations."""
        delta = timedelta(hours=2, minutes=30)
        assert format_time_since(delta) == "2 hours, 30 minutes"
        
        delta = timedelta(hours=1, minutes=1)
        assert format_time_since(delta) == "1 hour, 1 minute"

    def test_days_only(self):
        """Test formatting for day-only durations."""
        delta = timedelta(days=3)
        assert format_time_since(delta) == "3 days"
        
        delta = timedelta(days=1)
        assert format_time_since(delta) == "1 day"

    def test_days_and_hours(self):
        """Test formatting for day and hour combinations."""
        delta = timedelta(days=2, hours=5)
        assert format_time_since(delta) == "2 days, 5 hours"
        
        delta = timedelta(days=1, hours=1)
        assert format_time_since(delta) == "1 day, 1 hour"

    def test_days_ignore_minutes(self):
        """Test that minutes are ignored when days are present."""
        delta = timedelta(days=2, hours=3, minutes=45)
        assert format_time_since(delta) == "2 days, 3 hours"