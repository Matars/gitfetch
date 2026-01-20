"""
Cache manager for storing GitHub data locally using SQLite
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages local caching of GitHub data using SQLite."""

    def __init__(self, cache_expiry_minutes: int = 15,
                 cache_dir: Optional[Path] = None):
        """
        Initialize the cache manager.

        Args:
            cache_expiry_minutes: Minutes before cache expires (default: 15)
            cache_dir: Directory to store cache files
                (default: ~/.local/share/gitfetch)
        """
        self.cache_expiry_minutes = cache_expiry_minutes
        self.CACHE_DIR = cache_dir or (
            Path.home() / ".local" / "share" / "gitfetch")
        self.DB_FILE = self.CACHE_DIR / "cache.db"
        self._ensure_cache_dir()
        self._init_database()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        self._ensure_cache_dir()
        with sqlite3.connect(self.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    user_data TEXT NOT NULL,
                    stats_data TEXT NOT NULL,
                    cached_at TIMESTAMP NOT NULL
                )
            ''')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_cached_at ON users(cached_at)'
            )
            conn.commit()

    def get_cached_user_data(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached user data if available and not expired.

        Args:
            username: GitHub username

        Returns:
            Cached user data or None if not available/expired
        """
        entry = self.get_cached_entry(username)
        return entry[0] if entry else None

    def get_cached_stats(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached statistics if available and not expired.

        Args:
            username: GitHub username

        Returns:
            Cached stats or None if not available/expired
        """
        entry = self.get_cached_entry(username)
        return entry[1] if entry else None

    def get_cached_entry(self, username: str) -> Optional[
            tuple[Dict[str, Any], Dict[str, Any]]
    ]:
        """
        Retrieve both user data and stats if available and not expired.

        Args:
            username: GitHub username

        Returns:
            Tuple of (user_data, stats) or None if not available/expired
        """
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT user_data, stats_data, cached_at FROM users '
                    'WHERE username = ?',
                    (username,)
                )
                row = cursor.fetchone()

            if not row:
                return None

            cached_at = datetime.fromisoformat(row[2])
            if self._is_cache_expired(cached_at):
                return None

            user_data = json.loads(row[0])
            stats_data = json.loads(row[1])
            return (user_data, stats_data)
        except (sqlite3.Error, json.JSONDecodeError, ValueError):
            return None

    def get_stale_cached_entry(self, username: str) -> Optional[
            tuple[Dict[str, Any], Dict[str, Any], datetime]
    ]:
        """
        Retrieve cached data even if expired (for background refresh).

        Args:
            username: GitHub username

        Returns:
            Tuple of (user_data, stats, cached_at) or None if not available
        """
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT user_data, stats_data, cached_at FROM users '
                    'WHERE username = ?',
                    (username,)
                )
                row = cursor.fetchone()

            if not row:
                return None

            cached_at = datetime.fromisoformat(row[2])
            user_data = json.loads(row[0])
            stats_data = json.loads(row[1])
            return (user_data, stats_data, cached_at)
        except (sqlite3.Error, json.JSONDecodeError, ValueError):
            return None

    def get_stale_cached_user_data(
        self, username: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached user data even if expired.

        Args:
            username: GitHub username

        Returns:
            Cached user data or None if not available
        """
        entry = self.get_stale_cached_entry(username)
        return entry[0] if entry else None

    def get_stale_cached_stats(self, username: str) -> Optional[
            Dict[str, Any]
    ]:
        """
        Retrieve cached statistics even if expired.

        Args:
            username: GitHub username

        Returns:
            Cached stats or None if not available
        """
        entry = self.get_stale_cached_entry(username)
        return entry[1] if entry else None

    def is_cache_stale(self, username: str) -> bool:
        """
        Check if cached data exists but is stale (expired).

        Args:
            username: GitHub username

        Returns:
            True if cache exists but is stale, False otherwise
        """
        entry = self.get_stale_cached_entry(username)
        if not entry:
            return False
        _, _, cached_at = entry
        return self._is_cache_expired(cached_at)

    def cache_user_data(self, username: str, user_data: Dict[str, Any],
                        stats: Dict[str, Any]) -> None:
        """
        Cache user data and statistics.

        Args:
            username: GitHub username
            user_data: User profile data to cache
            stats: Statistics data to cache
        """
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users
                    (username, user_data, stats_data, cached_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    username,
                    json.dumps(user_data),
                    json.dumps(stats),
                    datetime.now().isoformat()
                ))
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Cache write failed for user '{username}': {e}")

    def clear(self) -> None:
        """Clear all cached data."""
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users')
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Cache clear failed: {e}")

    def clear_user(self, username: str) -> None:
        """
        Clear cached data for a specific user.

        Args:
            username: GitHub username to clear from cache
        """
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE username = ?', (username,))
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Cache clear failed for user '{username}': {e}")

    def _is_cache_expired(self, cached_at: datetime) -> bool:
        """
        Check if cache timestamp has expired.

        Args:
            cached_at: Timestamp when data was cached

        Returns:
            True if expired, False otherwise
        """
        # Defensive handling: ensure cache_expiry_minutes is a reasonable int
        # and avoid passing an extremely large integer to timedelta which can
        # raise OverflowError on some platforms (assuming on 32-bit builds).
        try:
            minutes = int(self.cache_expiry_minutes)
        except Exception:
            minutes = 15

        # Enforce sensible bounds: minimum 1 minute, cap to MAX_MINUTES
        # (10 years expressed in minutes). This prevents OverflowError while
        # still allowing very long cache durations when intentionally set.
        MAX_MINUTES = 5256000  # 10 years
        minutes = max(1, min(minutes, MAX_MINUTES))

        try:
            expiry_time = datetime.now() - timedelta(minutes=minutes)
        except OverflowError:
            # In the unlikely event timedelta still overflows, treat cache as
            # non-expired (safe default) to avoid crashing the program.
            return False

        return cached_at < expiry_time

    def list_cached_accounts(self) -> list[tuple[str, datetime]]:
        """
        List all cached GitHub accounts with their cache timestamps.

        Returns:
            List of tuples (username, cached_at)
        """
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username, cached_at FROM users')
                rows = cursor.fetchall()

            result = []
            for row in rows:
                try:
                    cached_at = datetime.fromisoformat(row[1])
                    result.append((row[0], cached_at))
                except ValueError:
                    logger.warning(f"Invalid cache timestamp for user '{row[0]}': {row[1]}")
                    continue
            return result
        except sqlite3.Error as e:
            logger.warning(f"Failed to list cached accounts: {e}")
            return []

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics (total entries, oldest, newest)
        """
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()

                # Get total entries
                cursor.execute('SELECT COUNT(*) FROM users')
                total = cursor.fetchone()[0]

                # Get oldest and newest entries
                cursor.execute(
                    'SELECT username, cached_at FROM users '
                    'ORDER BY cached_at ASC LIMIT 1'
                )
                oldest = cursor.fetchone()

                cursor.execute(
                    'SELECT username, cached_at FROM users '
                    'ORDER BY cached_at DESC LIMIT 1'
                )
                newest = cursor.fetchone()

            return {
                "total_entries": total,
                "oldest_entry": oldest[0] if oldest else None,
                "newest_entry": newest[0] if newest else None
            }
        except sqlite3.Error as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {
                "total_entries": 0,
                "oldest_entry": None,
                "newest_entry": None
            }

    def _execute_query(self, query: str, params: tuple = ()) -> Optional[Any]:
        """
        Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results or None
        """
        try:
            with sqlite3.connect(self.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall()
                conn.commit()
                return result
        except sqlite3.Error as e:
            logger.warning(f"Query execution failed: {e}")
            return None

    def close(self) -> None:
        """Close database connection."""
        # SQLite connections are created per-operation, so nothing to close
        pass
