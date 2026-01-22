"""
Tests for CLI functionality
"""

import time
from unittest.mock import patch, MagicMock

from gitfetch.cli import Spinner


class TestSpinner:
    """Test cases for Spinner class."""

    def test_spinner_init(self):
        """Test Spinner initialization."""
        spinner = Spinner("Test message")
        assert spinner.message == "Test message"
        assert spinner._spinner_thread is None
        assert not spinner._stop_event.is_set()

    def test_spinner_frames(self):
        """Test that spinner has frames defined."""
        assert len(Spinner.SPINNER_FRAMES) == 10
        assert all(isinstance(frame, str) for frame in Spinner.SPINNER_FRAMES)

    def test_spinner_context_manager(self):
        """Test spinner as context manager."""
        spinner = Spinner("Loading...")

        with patch('sys.stdout') as mock_stdout:
            with spinner:
                # Spin for a very short time
                time.sleep(0.05)

        # Verify thread was cleaned up
        assert spinner._spinner_thread is None

    def test_spinner_start_stop(self):
        """Test manual start/stop."""
        spinner = Spinner("Test")

        with patch('sys.stdout'):
            spinner.start()
            assert spinner._spinner_thread is not None
            time.sleep(0.05)  # Let it spin briefly
            spinner.stop()
            assert spinner._spinner_thread is None

    def test_run_with_spinner(self):
        """Test static method for running function with spinner."""
        def test_func():
            time.sleep(0.05)
            return 42

        with patch('sys.stdout'):
            result = Spinner.run_with_spinner("Computing...", test_func)

        assert result == 42

    def test_run_with_spinner_exception(self):
        """Test that exceptions are propagated through spinner."""
        def failing_func():
            raise ValueError("Test error")

        with patch('sys.stdout'):
            try:
                Spinner.run_with_spinner("Failing...", failing_func)
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert str(e) == "Test error"
