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
        default_colors = {
            'reset': '\\033[0m',
            'bold': '\\033[1m',
            'dim': '\\033[2m',
            'red': '\\033[91m',
            'green': '\\033[92m',
            'yellow': '\\033[93m',
            'blue': '\\033[94m',
            'magenta': '\\033[95m',
            'cyan': '\\033[96m',
            'white': '\\033[97m',
            'orange': '\\033[38;2;255;165;0m',
            'accent': '\\033[1m',
            'header': '\\033[38;2;118;215;161m',
            'muted': '\\033[2m',
            '0': '\\033[48;5;238m',
            '1': '\\033[48;5;28m',
            '2': '\\033[48;5;34m',
            '3': '\\033[48;5;40m',
            '4': '\\033[48;5;82m'
        }
        if self.CONFIG_FILE.exists():
            self.config.read(self.CONFIG_FILE)
            if "COLORS" in self.config:
                self.config._sections['COLORS'] = {
                    **default_colors, **self.config._sections['COLORS']}
            else:
                self.config._sections['COLORS'] = default_colors
        else:
            # Create default config
            self.config['DEFAULT'] = {
                'username': '',
                'cache_expiry_hours': '24'
            }
            self.config.add_section('COLORS')
            for key, value in default_colors.items():
                self.config.set('COLORS', key, value)
        for k, v in self.config._sections['COLORS'].items():
            self.config._sections['COLORS'][k] = v.encode(
                'utf-8').decode('unicode_escape')

    def get_default_username(self) -> Optional[str]:
        """
        Get the default GitHub username from config.

        Returns:
            Default username or None if not set
        """
        username = self.config.get('DEFAULT', 'username', fallback='')
        return username if username else None

    def get_colors(self) -> dict:
        """
        Get colors

        Returns:
            User defined colors or default colors if not set
        """
        return self.config._sections["COLORS"]

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
            True if config exists and has default username and provider
        """
        return (self.CONFIG_FILE.exists() and
                bool(self.get_default_username()) and
                bool(self.get_provider()))

    def get_provider(self) -> Optional[str]:
        """
        Get the git provider from config.

        Returns:
            Provider name (github, gitlab, gitea, etc.) or None if not set
        """
        provider = self.config.get('DEFAULT', 'provider', fallback='')
        return provider if provider else None

    def set_provider(self, provider: str) -> None:
        """
        Set the git provider in config.

        Args:
            provider: Git provider name (github, gitlab, gitea, etc.)
        """
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['provider'] = provider

    def get_provider_url(self) -> Optional[str]:
        """
        Get the provider base URL from config.

        Returns:
            Base URL for the git provider or None if not set
        """
        url = self.config.get('DEFAULT', 'provider_url', fallback='')
        return url if url else None

    def set_provider_url(self, url: str) -> None:
        """
        Set the provider base URL in config.

        Args:
            url: Base URL for the git provider
        """
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['provider_url'] = url

    def save(self) -> None:
        """Save configuration to file."""
        import os
        self._ensure_config_dir()
        # Remove the file if it exists to ensure clean write
        if self.CONFIG_FILE.exists():
            os.remove(self.CONFIG_FILE)
        with open(self.CONFIG_FILE, 'w') as f:
            f.write("# gitfetch configuration file\n")
            f.write("# See docs/providers.md for provider configuration\n")
            f.write("# See docs/colors.md for color customization\n\n")

            f.write("[DEFAULT]\n")
            username = self.config.get('DEFAULT', 'username', fallback='')
            f.write(f"username = {username}\n\n")

            cache_hours = self.config.get('DEFAULT', 'cache_expiry_hours',
                                          fallback='24')
            f.write(f"cache_expiry_hours = {cache_hours}\n\n")

            provider = self.config.get('DEFAULT', 'provider', fallback='')
            f.write(f"provider = {provider}\n\n")

            provider_url = self.config.get('DEFAULT', 'provider_url',
                                           fallback='')
            f.write(f"provider_url = {provider_url}\n\n")

            if 'COLORS' in self.config:
                f.write("[COLORS]\n")
                for key, value in self.config['COLORS'].items():
                    f.write(f"{key} = {value}\n")
                f.write("\n")
            f.write("\n")
