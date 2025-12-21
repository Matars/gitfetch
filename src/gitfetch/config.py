"""
Configuration manager for gitfetch
"""

import configparser
import os
from pathlib import Path
from typing import Optional
import webcolors

from .providers import ProviderConfig, PROVIDER_ENV_VARS, PROVIDER_DEFAULT_URLS

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
            'reset': '#000000',
            'bold': '#FFFFFF',
            'dim': '#888888',
            'red': '#FF5555',
            'green': '#50FA7B',
            'yellow': '#F1FA8C',
            'blue': '#BD93F9',
            'magenta': '#FF79C6',
            'cyan': '#8BE9FD',
            'white': '#F8F8F2',
            'orange': '#FFB86C',
            'accent': '#FFFFFF',
            'header': '#76D7A1',
            'muted': '#44475A',
            # Contribution intensity levels (GitHub-like defaults)
            '0': '#ebedf0',  # no contributions / very light gray
            '1': '#9be9a8',  # light
            '2': '#40c463',  # medium
            '3': '#30a14e',  # darker
            '4': '#216e39'   # darkest
        }
        if self.CONFIG_FILE.exists():
            self.config.read(self.CONFIG_FILE)
            # Migrate old cache_expiry_hours to cache_expiry_minutes
            if self.config.has_option('DEFAULT', 'cache_expiry_hours'):
                old_hours = self.config.get('DEFAULT', 'cache_expiry_hours')
                try:
                    new_minutes = int(old_hours) * 60  # hours to minutes
                    self.config.set('DEFAULT', 'cache_expiry_minutes',
                                    str(new_minutes))
                    self.config.remove_option('DEFAULT', 'cache_expiry_hours')
                    self.save()  # Save migrated config
                except ValueError:
                    pass  # Keep default if invalid
            if "COLORS" in self.config._sections:
                # Filter out non-color keys that might have been corrupted
                colors_data = self.config._sections['COLORS']
                valid_color_keys = set(default_colors.keys())
                filtered_colors = {k: v for k, v in colors_data.items()
                                   if k in valid_color_keys}
                self.config._sections['COLORS'] = {
                    **default_colors, **filtered_colors}
            else:
                self.config.add_section('COLORS')
                for key, value in default_colors.items():
                    self.config.set('COLORS', key, value)
        else:
            # Create default config
            self.config['DEFAULT'] = {
                'username': '',
                'cache_expiry_minutes': '15',
                'token': '',
            }
            self.config.add_section('COLORS')
            for key, value in default_colors.items():
                self.config.set('COLORS', key, value)
        # No longer decode ANSI escapes; store as hex

    def get_default_username(self) -> Optional[str]:
        """
        Get the default username from config.

        Returns:
            Default username or None if not set
        """
        username = self.config.get('DEFAULT', 'username', fallback='')
        return username if username else None

    def get_colors(self) -> dict:
        """
        Get colors as hex codes from config.

        Returns:
            dict: color name to hex code
        """
        parsed = {}
        for k,v in self.config._sections["COLORS"].items():
            if not v.startswith("#") and v in webcolors.names():
                parsed[k] = webcolors.name_to_hex(v)
            else:
                parsed[k] = v
        return parsed

    def get_ansi_colors(self) -> dict:
        """
        Get colors as ANSI escape codes for terminal output.

        Returns:
            dict: color name to ANSI code
        """
        # Map hex codes to ANSI codes (basic mapping for demonstration)
        hex_to_ansi = {
            '#000000': '\033[0m',
            '#FFFFFF': '\033[1m',
            '#888888': '\033[2m',
            '#FF5555': '\033[91m',
            '#50FA7B': '\033[92m',
            '#F1FA8C': '\033[93m',
            '#BD93F9': '\033[94m',
            '#FF79C6': '\033[95m',
            '#8BE9FD': '\033[96m',
            '#F8F8F2': '\033[97m',
            '#FFB86C': '\033[38;2;255;184;108m',
            '#76D7A1': '\033[38;2;118;215;161m',
            '#44475A': '\033[38;2;68;71;90m',
            '#282A36': '\033[48;5;238m',
            '#6272A4': '\033[38;2;98;114;164m',
        }
        colors = self.get_colors()
        ansi_colors = {}
        for key, value in colors.items():
            ansi_colors[key] = hex_to_ansi.get(value, value)
        return ansi_colors

    def set_default_username(self, username: str) -> None:
        """
        Set the default username in config.

        Args:
            username: Username to set as default
        """
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['username'] = username

    def get_cache_expiry_minutes(self) -> int:
        """
        Get cache expiry time in minutes.

        Returns:
            Number of minutes before cache expires (minimum 1)
        """
        minutes_str = self.config.get(
            'DEFAULT', 'cache_expiry_minutes', fallback='15')
        try:
            minutes = int(minutes_str)
            # Ensure cache expiry is at least 1 minute
            return max(1, minutes)
        except ValueError:
            return 15

    def set_cache_expiry_minutes(self, minutes: int) -> None:
        """
        Set cache expiry time in minutes.

        Args:
            minutes: Number of minutes before cache expires (minimum 1)
        """
        # Ensure cache expiry is at least 1 minute
        minutes = max(1, minutes)

        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['cache_expiry_minutes'] = str(minutes)

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

    def get_custom_box(self) -> Optional[str]:
        """
        Get the custom box character from config.

        Returns:
            Custom box character or None if not set
        """
        box = self.config.get('DEFAULT', 'custom_box', fallback='')
        return box if box else None

    def set_custom_box(self, box: str) -> None:
        """
        Set the custom box character in config.

        Args:
            box: Custom box character to use
        """
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['custom_box'] = box

    def get_token(self) -> Optional[str]:
        """
        Get the personal access token from config.

        Returns:
            Token or None if not set
        """
        token = self.config.get('DEFAULT', 'token', fallback='')
        return token if token else None

    def set_token(self, token: str) -> None:
        """
        Set the personal access token in config.

        Args:
            token: Personal access token
        """
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['token'] = token

    def get_provider_config(self) -> Optional[ProviderConfig]:
        """
        Get complete provider configuration with token resolution.

        Token resolution chain:
        1. Read from provider section
        2. Fall back to environment variable

        Returns:
            ProviderConfig with resolved token, or None if no provider set
        """
        provider_name = self.get_provider()
        if not provider_name:
            return None

        section = provider_name  # e.g., "github"

        # Try provider section first, fall back to DEFAULT for backward compat
        if self.config.has_section(section):
            username = self.config.get(section, 'username', fallback='')
            url = self.config.get(section, 'url', fallback='')
            token = self.config.get(section, 'token', fallback='')
        else:
            # Backward compatibility: read from DEFAULT
            username = self.get_default_username() or ''
            url = self.get_provider_url() or ''
            token = self.get_token() or ''

        # Token resolution: config -> env var
        if not token:
            env_var = PROVIDER_ENV_VARS.get(provider_name, '')
            if env_var:
                token = os.getenv(env_var, '') or ''

        # Use default URL if not specified
        if not url:
            url = PROVIDER_DEFAULT_URLS.get(provider_name, '')

        return ProviderConfig(
            name=provider_name,
            username=username,
            url=url,
            token=token
        )

    def set_provider_config(self, config: ProviderConfig) -> None:
        """
        Save provider configuration to its dedicated section.

        Args:
            config: ProviderConfig to save
        """
        section = config.name
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, 'username', config.username)
        self.config.set(section, 'url', config.url)
        self.config.set(section, 'token', config.token)

        # Also set provider in DEFAULT
        self.set_provider(config.name)

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
            f.write(f"username = {username}\n")

            cache_minutes = self.config.get('DEFAULT', 'cache_expiry_minutes',
                                            fallback='15')
            f.write(f"cache_expiry_minutes = {cache_minutes}\n")

            provider = self.config.get('DEFAULT', 'provider', fallback='')
            f.write(f"provider = {provider}\n")

            provider_url = self.config.get('DEFAULT', 'provider_url',
                                           fallback='')
            f.write(f"provider_url = {provider_url}\n")

            token = self.config.get('DEFAULT', 'token', fallback='')
            if token:
                f.write(f"token = {token}\n")

            custom_box = self.config.get('DEFAULT', 'custom_box', fallback='')
            if custom_box:
                f.write(f"custom_box = {custom_box}\n")

            show_date = self.config.get('DEFAULT', 'show_date',
                                        fallback='true')
            if show_date != 'true':  # Only write if it's not the default
                f.write(f"show_date = {show_date}\n")

            f.write("\n")

            # Write all provider sections (empty if not configured)
            known_providers = ['github', 'gitlab', 'gitea', 'sourcehut']
            for provider_section in known_providers:
                f.write(f"[{provider_section}]\n")
                for key in ['username', 'url', 'token']:
                    value = self.config.get(provider_section, key,
                                            fallback='') if self.config.has_section(provider_section) else ''
                    f.write(f"{key} = {value}\n")
                f.write("\n")

            if 'COLORS' in self.config._sections:
                f.write("[COLORS]\n")
                # Find the longest key for alignment
                colors_section = self.config._sections['COLORS']
                if colors_section:
                    keys = list(colors_section.keys())
                    max_key_length = max(len(key) for key in keys)
                    for key, value in colors_section.items():
                        f.write(f"{key:<{max_key_length}} = {value}\n")
                f.write("\n")
