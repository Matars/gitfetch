"""
Tests for display functionality
"""

import sys
from unittest.mock import patch, MagicMock
from gitfetch.config import ConfigManager


class TestDisplayHelpers:
    """Test cases for display helper functions (without full initialization)."""

    def test_calculate_streaks_empty_data(self):
        """Test streak calculation with empty data."""
        # Import here to avoid initialization issues
        from gitfetch.display import DisplayFormatter
        
        # We can test the static method directly by using a minimal mock
        weeks_data = []
        
        # The method needs to be called on an instance, so we'll patch the init
        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            current, max_streak = formatter._calculate_streaks(weeks_data)
            assert current == 0
            assert max_streak == 0

    def test_calculate_streaks_no_contributions(self):
        """Test streak calculation with no contributions."""
        from gitfetch.display import DisplayFormatter
        
        weeks_data = [
            {'contributionDays': [
                {'contributionCount': 0},
                {'contributionCount': 0},
            ]}
        ]
        
        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            current, max_streak = formatter._calculate_streaks(weeks_data)
            assert current == 0
            assert max_streak == 0

    def test_calculate_streaks_active_streak(self):
        """Test current streak calculation."""
        from gitfetch.display import DisplayFormatter

        # Data is in chronological order; function reverses to get newest first
        # 0, 3, 5 reversed -> 5, 3, 0, so current streak is 0 (most recent is 0)
        weeks_data = [
            {'contributionDays': [
                {'contributionCount': 0},
                {'contributionCount': 3},
                {'contributionCount': 5},
            ]}
        ]

        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            current, max_streak = formatter._calculate_streaks(weeks_data)
            assert current == 2  # Two consecutive days with contributions at the end

    def test_calculate_streaks_max_streak(self):
        """Test max streak calculation."""
        from gitfetch.display import DisplayFormatter
        
        weeks_data = [
            {'contributionDays': [
                {'contributionCount': 5},
                {'contributionCount': 3},
                {'contributionCount': 0},
                {'contributionCount': 7},
                {'contributionCount': 4},
                {'contributionCount': 2},
            ]}
        ]
        
        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            current, max_streak = formatter._calculate_streaks(weeks_data)
            assert current == 3  # Current streak at end
            assert max_streak == 3  # Max streak is 3

    def test_calculate_total_contributions(self):
        """Test total contributions calculation."""
        from gitfetch.display import DisplayFormatter
        
        weeks_data = [
            {'contributionDays': [
                {'contributionCount': 5},
                {'contributionCount': 3},
                {'contributionCount': 0},
            ]},
            {'contributionDays': [
                {'contributionCount': 2},
                {'contributionCount': 4},
            ]}
        ]
        
        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            total = formatter._calculate_total_contributions(weeks_data)
            assert total == 14  # 5 + 3 + 0 + 2 + 4

    def test_format_date_valid(self):
        """Test date formatting with valid input."""
        from gitfetch.display import DisplayFormatter
        
        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            result = formatter._format_date("2024-01-15T10:30:00Z")
            assert "January" in result
            assert "15" in result
            assert "2024" in result

    def test_format_date_invalid(self):
        """Test date formatting with invalid input."""
        from gitfetch.display import DisplayFormatter
        
        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            result = formatter._format_date("invalid-date")
            assert result == "invalid-date"

    def test_format_date_out_of_range(self):
        """Test date formatting with out of range year."""
        from gitfetch.display import DisplayFormatter
        
        with patch.object(DisplayFormatter, '__init__', lambda self, cm, **kwargs: None):
            formatter = DisplayFormatter(None)
            result = formatter._format_date("1800-01-15T10:30:00Z")
            assert result == "1800-01-15T10:30:00Z"
