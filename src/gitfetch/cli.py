"""
Command-line interface for gitfetch
"""

import argparse
import sys
from typing import Optional

from .fetcher import GitHubFetcher
from .display import DisplayFormatter
from .cache import CacheManager
from .config import ConfigManager
from . import __version__


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="A neofetch-style CLI tool for GitHub statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "username",
        nargs="?",
        help="GitHub username to fetch stats for"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cache and fetch fresh data"
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the cache and exit"
    )

    parser.add_argument(
        "--token",
        type=str,
        help="GitHub personal access token (optional, increases rate limits)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for the CLI."""
    args = parse_args()

    # Initialize config
    config_manager = ConfigManager()

    # Check if gitfetch is initialized
    if not config_manager.is_initialized():
        print("🚀 Welcome to gitfetch! Let's set up your configuration.\n")
        if not _initialize_gitfetch(config_manager):
            print("Error: Initialization failed", file=sys.stderr)
            return 1
        print("\n✅ Configuration saved! You can now use gitfetch.\n")

    # Initialize components
    cache_expiry = config_manager.get_cache_expiry_hours()
    cache_manager = CacheManager(cache_expiry_hours=cache_expiry)
    fetcher = GitHubFetcher()  # Uses gh CLI, no token needed
    formatter = DisplayFormatter()

    # Handle cache clearing
    if args.clear_cache:
        cache_manager.clear()
        print("Cache cleared successfully!")
        return 0

    # Get username
    username = args.username
    if not username:
        # Try to get default username from config
        username = config_manager.get_default_username()
        if not username:
            username = _prompt_username()
            if not username:
                print("Error: Username is required", file=sys.stderr)
                return 1

    # Fetch data (with or without cache)
    try:
        if args.no_cache:
            user_data = fetcher.fetch_user_data(username)
            stats = fetcher.fetch_user_stats(username, user_data)
            cache_manager.cache_user_data(username, user_data, stats)
        else:
            # Try to get fresh cache first
            user_data = cache_manager.get_cached_user_data(username)
            stats = cache_manager.get_cached_stats(username)

            if user_data is None or stats is None:
                # No fresh cache, try to get stale cache for immediate display
                stale_user_data = cache_manager.get_stale_cached_user_data(
                    username
                )
                stale_stats = cache_manager.get_stale_cached_stats(username)

                if stale_user_data is not None and stale_stats is not None:
                    # Display stale cache immediately
                    formatter.display(username, stale_user_data, stale_stats)
                    print("\n🔄 Refreshing data in background...",
                          file=sys.stderr)

                    # Refresh cache in background (don't wait for it)
                    import threading

                    def refresh_cache():
                        try:
                            fresh_user_data = fetcher.fetch_user_data(username)
                            fresh_stats = fetcher.fetch_user_stats(
                                username, fresh_user_data
                            )
                            cache_manager.cache_user_data(
                                username, fresh_user_data, fresh_stats
                            )
                        except Exception:
                            pass  # Silently fail background refresh

                    thread = threading.Thread(
                        target=refresh_cache, daemon=True
                    )
                    thread.start()
                    return 0
                else:
                    # No cache at all, fetch fresh data
                    user_data = fetcher.fetch_user_data(username)
                    stats = fetcher.fetch_user_stats(username, user_data)
                    cache_manager.cache_user_data(username, user_data, stats)
            # else: fresh cache available, proceed to display

        # Display the results
        formatter.display(username, user_data, stats)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _prompt_username() -> Optional[str]:
    """Prompt user for GitHub username if not provided."""
    try:
        username = input("Enter GitHub username: ").strip()
        return username if username else None
    except (KeyboardInterrupt, EOFError):
        print()
        return None


def _initialize_gitfetch(config_manager: ConfigManager) -> bool:
    """
    Initialize gitfetch by creating config directory and asking for
    default username.

    Args:
        config_manager: ConfigManager instance

    Returns:
        True if initialization succeeded, False otherwise
    """
    try:
        # Prompt for default username
        print("Please enter your default GitHub username.")
        print("(You can override this later by passing a username as "
              "an argument)")
        username = input("\nGitHub username: ").strip()

        if not username:
            print("Error: Username cannot be empty", file=sys.stderr)
            return False

        # Save configuration
        config_manager.set_default_username(username)
        config_manager.save()

        return True

    except (KeyboardInterrupt, EOFError):
        print("\nInitialization cancelled.")
        return False
    except Exception as e:
        print(f"Error during initialization: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())
