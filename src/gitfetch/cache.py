"""
Cache manager for storing GitHub data locally using SQLite
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json


class CacheManager:
    """Manages local caching of GitHub data using SQLite."""

    CACHE_DIR = Path.home() / ".config" / "gitfetch"
    DB_FILE = CACHE_DIR / "cache.db"

    def __init__(self, cache_expiry_hours: int = 24):
        """
        Initialize the cache manager.

        Args:
            cache_expiry_hours: Hours before cache expires (default: 24)
        """
        self.cache_expiry_hours = cache_expiry_hours
        self._ensure_cache_dir()
        self._init_database()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        self._ensure_cache_dir()
        conn = sqlite3.connect(self.DB_FILE)
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
        conn.close()

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

    def get_cached_entry(self, username: str) -> Optional[tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Retrieve both user data and stats if available and not expired.

        Args:
            username: GitHub username

        Returns:
            Tuple of (user_data, stats) or None if not available/expired
        """
        try:
            conn = sqlite3.connect(self.DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT user_data, stats_data, cached_at FROM users '
                'WHERE username = ?',
                (username,)
            )
            row = cursor.fetchone()
            conn.close()

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
            conn = sqlite3.connect(self.DB_FILE)
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
            conn.close()
        except sqlite3.Error:
            pass  # Silently fail on cache errors

    def clear(self) -> None:
        """Clear all cached data."""
        try:
            conn = sqlite3.connect(self.DB_FILE)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users')
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def clear_user(self, username: str) -> None:
        """
        Clear cached data for a specific user.

        Args:
            username: GitHub username to clear from cache
        """
        try:
            conn = sqlite3.connect(self.DB_FILE)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def _is_cache_expired(self, cached_at: datetime) -> bool:
        """
        Check if cache timestamp has expired.

        Args:
            cached_at: Timestamp when data was cached

        Returns:
            True if expired, False otherwise
        """
        expiry_time = datetime.now() - timedelta(hours=self.cache_expiry_hours)
        return cached_at < expiry_time

    def list_cached_accounts(self) -> list[tuple[str, datetime]]:
        """
        List all cached GitHub accounts with their cache timestamps.

        Returns:
            List of tuples (username, cached_at)
        """
        try:
            conn = sqlite3.connect(self.DB_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT username, cached_at FROM users')
            rows = cursor.fetchall()
            conn.close()

            result = []
            for row in rows:
                try:
                    cached_at = datetime.fromisoformat(row[1])
                    result.append((row[0], cached_at))
                except ValueError:
                    continue
            return result
        except sqlite3.Error:
            return []

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics (total entries, oldest, newest)
        """
        try:
            conn = sqlite3.connect(self.DB_FILE)
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

            conn.close()

            return {
                "total_entries": total,
                "oldest_entry": oldest[0] if oldest else None,
                "newest_entry": newest[0] if newest else None
            }
        except sqlite3.Error:
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
            conn = sqlite3.connect(self.DB_FILE)
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.commit()
            conn.close()
            return result
        except sqlite3.Error:
            return None

    def close(self) -> None:
        """Close database connection."""
        # SQLite connections are created per-operation, so nothing to close
        pass
