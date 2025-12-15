"""
Tests for cache functionality
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from gitfetch.cache import CacheManager


class TestCacheManager:
    """Test cases for CacheManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(
            cache_expiry_minutes=15, cache_dir=Path(self.temp_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_expiry(self):
        """Test that cache expires after specified time."""
        username = "testuser"
        user_data = {"login": "testuser", "name": "Test User"}
        stats = {"repositories": 10, "stars": 5}

        # Cache data
        self.cache_manager.cache_user_data(username, user_data, stats)

        # Should be available immediately
        cached_data = self.cache_manager.get_cached_user_data(username)
        assert cached_data == user_data

        # Mock _is_cache_expired to return True (expired)
        with patch.object(self.cache_manager, '_is_cache_expired',
                          return_value=True):
            # Should be expired
            cached_data = self.cache_manager.get_cached_user_data(username)
            assert cached_data is None

    def test_stale_cache_retrieval(self):
        """Test retrieving stale cache for background refresh."""
        username = "testuser"
        user_data = {"login": "testuser", "name": "Test User"}
        stats = {"repositories": 10, "stars": 5}

        # Cache data
        self.cache_manager.cache_user_data(username, user_data, stats)

        # Should get stale data even when expired
        stale_data = self.cache_manager.get_stale_cached_user_data(username)
        assert stale_data == user_data

    def test_cache_minutes_parameter(self):
        """Test that cache_expiry_minutes parameter works."""
        cache_manager = CacheManager(
            cache_expiry_minutes=30, cache_dir=Path(self.temp_dir))
        assert cache_manager.cache_expiry_minutes == 30

    def test_cache_timestamp_update(self):
        """Test that caching updates the timestamp."""
        username = "testuser"
        user_data = {"login": "testuser", "name": "Test User"}
        stats = {"repositories": 10, "stars": 5}

        # Cache data initially
        self.cache_manager.cache_user_data(username, user_data, stats)

        # Get the initial timestamp
        initial_entry = self.cache_manager.get_stale_cached_entry(username)
        assert initial_entry is not None
        _, _, initial_timestamp = initial_entry

        # Wait a tiny bit and cache again
        import time
        time.sleep(0.001)  # Ensure timestamp difference

        # Cache the same data again
        self.cache_manager.cache_user_data(username, user_data, stats)

        # Get the updated timestamp
        updated_entry = self.cache_manager.get_stale_cached_entry(username)
        assert updated_entry is not None
        _, _, updated_timestamp = updated_entry

        # Timestamps should be different
        assert updated_timestamp > initial_timestamp

        # Remove test user cache
        self.cache_manager.clear_user(username)
