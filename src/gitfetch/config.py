"""
Configuration manager for gitfetch
"""

import configparser
from pathlib import Path
from typing import Optional


class ConfigManager:
    """Manages gitfetch configuration."""

    CONFIG_DIR = Path.home() / ".config" / "gitfetch"
    CONFIG_FILE = CONFIG_DIR / "gitfetch.conf"

    def __init__(self):
        """Initialize the configuration manager."""
        self.config = configparser.ConfigParser()
        self._ensure_config_dir()
        self._load_config()

    def _ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> None:
        """Load configuration from file."""
        if self.CONFIG_FILE.exists():
            self.config.read(self.CONFIG_FILE)
        else:
            # Create default config
            self.config['DEFAULT'] = {
                'username': '',
                'cache_expiry_hours': '24'
            }

    def get_default_username(self) -> Optional[str]:
        """
        Get the default GitHub username from config.

        Returns:
            Default username or None if not set
        """
        username = self.config.get('DEFAULT', 'username', fallback='')
        return username if username else None

    def set_default_username(self, username: str) -> None:
        """
        Set the default GitHub username in config.

        Args:
            username: GitHub username to set as default
        """
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['username'] = username

    def get_cache_expiry_hours(self) -> int:
        """
        Get cache expiry time in hours.

        Returns:
            Number of hours before cache expires
        """
        hours_str = self.config.get(
            'DEFAULT', 'cache_expiry_hours', fallback='24')
        try:
            return int(hours_str)
        except ValueError:
            return 24

    def set_cache_expiry_hours(self, hours: int) -> None:
        """
        Set cache expiry time in hours.

        Args:
            hours: Number of hours before cache expires
        """
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['cache_expiry_hours'] = str(hours)

    def is_initialized(self) -> bool:
        """
        Check if gitfetch has been initialized.

        Returns:
            True if config exists and has default username
        """
        return self.CONFIG_FILE.exists() and bool(self.get_default_username())

    def save(self) -> None:
        """Save configuration to file."""
        self._ensure_config_dir()
        with open(self.CONFIG_FILE, 'w') as f:
            self.config.write(f)
