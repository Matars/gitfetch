"""Tests for the predefined text/shape pixel patterns."""

from gitfetch.text_patterns import CHAR_PATTERNS


class TestPatternGridContract:
    """Every pattern must be a 7-row grid (one row per weekday)."""

    def test_all_patterns_have_seven_rows(self):
        """The module documents 7-row grids and the renderer indexes rows 0-6."""
        bad = {
            name: len(pattern)
            for name, pattern in CHAR_PATTERNS.items()
            if len(pattern) != 7
        }
        assert not bad, f"patterns must have exactly 7 rows: {bad}"

    def test_all_pattern_rows_have_consistent_width(self):
        """Ragged rows would raise IndexError when building week columns."""
        bad = {
            name: sorted({len(row) for row in pattern})
            for name, pattern in CHAR_PATTERNS.items()
            if len({len(row) for row in pattern}) != 1
        }
        assert not bad, f"pattern rows must share one width: {bad}"

    def test_shape_grids_cover_all_rows(self):
        """Every row of a shape grid must survive week generation."""
        from gitfetch.display import DisplayFormatter

        formatter = DisplayFormatter.__new__(DisplayFormatter)
        formatter.text_patterns = None
        grid = formatter._shape_to_grid(["octocat"])
        assert len(grid) == 7
        weeks = formatter._generate_weeks_from_text_grid(grid)
        assert len(weeks) == len(grid[0])
        for week in weeks:
            assert len(week["contributionDays"]) == 7
