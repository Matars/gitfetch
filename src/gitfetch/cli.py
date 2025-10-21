"""
Command-line interface for gitfetch
"""

import argparse
import sys
from typing import Optional

import readchar

from .display import DisplayFormatter
from .cache import CacheManager
from .config import ConfigManager
from . import __version__


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="""A neofetch-style CLI tool for git.
Supports GitHub, GitLab, Gitea, and Sourcehut.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "username",
        nargs="?",
        help="Username to fetch stats for"
    )

    general_group = parser.add_argument_group('General Options')
    general_group.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cache and fetch fresh data"
    )

    general_group.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the cache and exit"
    )

    general_group.add_argument(
        "--token",
        type=str,
        help="Personal access token (optional, increases rate limits)"
    )

    general_group.add_argument(
        "--version",
        action="store_true",
        help="Show version and check for updates"
    )

    visual_group = parser.add_argument_group('Visual Options')
    visual_group.add_argument(
        "--spaced",
        action="store_true",
        help="Enable spaced layout"
    )

    visual_group.add_argument(
        "--not-spaced",
        action="store_true",
        help="Disable spaced layout"
    )

    visual_group.add_argument(
        "--custom-box",
        type=str,
        help="Custom character for contribution blocks (e.g., '■', '█')"
    )

    visual_group.add_argument(
        "--no-date",
        action="store_true",
        help="Hide month/date labels on contribution graph"
    )

    visual_group.add_argument(
        "--graph-only",
        action="store_true",
        help="Show only the contribution graph"
    )

    visual_group.add_argument(
        "--no-achievements",
        action="store_true",
        help="Hide achievements section"
    )

    visual_group.add_argument(
        "--no-languages",
        action="store_true",
        help="Hide languages section"
    )

    visual_group.add_argument(
        "--no-issues",
        action="store_true",
        help="Hide issues section"
    )

    visual_group.add_argument(
        "--no-pr",
        action="store_true",
        help="Hide pull requests section"
    )

    visual_group.add_argument(
        "--no-account",
        action="store_true",
        help="Hide account information section"
    )

    visual_group.add_argument(
        "--no-grid",
        action="store_true",
        help="Hide contribution grid/graph"
    )

    visual_group.add_argument(
        "--width",
        type=int,
        help="Set custom width for contribution graph"
    )

    visual_group.add_argument(
        "--height",
        type=int,
        help="Set custom height for contribution graph"
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.version:
        print(f"gitfetch version: {__version__}")
        # Check for updates from GitHub
        import requests
        try:
            resp = requests.get(
                "https://api.github.com/repos/Matars/gitfetch/releases/latest", timeout=3)
            if resp.status_code == 200:
                latest = resp.json()["tag_name"].lstrip("v")
                if latest != __version__:
                    print(
                        f"\033[93mUpdate available: {latest}\n"
                        "Get it at: https://github.com/Matars/gitfetch/releases/latest\n"
                        "Or run: brew update && brew upgrade gitfetch\033[0m")
                else:
                    print("You are using the latest version.")
            else:
                print("Could not check for updates.")
        except Exception:
            print("Could not check for updates.")
        return 0

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
    provider = config_manager.get_provider()
    provider_url = config_manager.get_provider_url()
    fetcher = _create_fetcher(provider, provider_url)

    # Handle custom box character
    custom_box = args.custom_box

    # Handle show date setting
    show_date = not args.no_date

    formatter = DisplayFormatter(config_manager, custom_box, show_date,
                                 args.graph_only, not args.no_achievements,
                                 not args.no_languages, not args.no_issues,
                                 not args.no_pr, not args.no_account,
                                 not args.no_grid, args.width, args.height)
    if args.spaced:
        spaced = True
    elif args.not_spaced:
        spaced = False
    else:
        spaced = True

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
            # Fall back to authenticated user
            try:
                username = fetcher.get_authenticated_user()
                # Save as default for future use
                config_manager.set_default_username(username)
                config_manager.save()
            except Exception:
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
            user_data = cache_manager.get_cached_user_data(username)
            stats = cache_manager.get_cached_stats(username)
            if user_data is None or stats is None:
                # Try to get stale cache for immediate display
                stale_user_data = cache_manager.get_stale_cached_user_data(
                    username)
                stale_stats = cache_manager.get_stale_cached_stats(username)
                if stale_user_data is not None and stale_stats is not None:
                    # Display stale cache immediately
                    formatter.display(username, stale_user_data,
                                      stale_stats, spaced=spaced)
                    print("\n🔄 Refreshing data in background...",
                          file=sys.stderr)

                    # Refresh cache in background (don't wait for it)
                    import threading

                    def refresh_cache():
                        try:
                            fresh_user_data = fetcher.fetch_user_data(username)
                            fresh_stats = fetcher.fetch_user_stats(
                                username, fresh_user_data)
                            cache_manager.cache_user_data(
                                username, fresh_user_data, fresh_stats)
                        except Exception:
                            pass
                    thread = threading.Thread(
                        target=refresh_cache, daemon=True)
                    thread.start()
                    return 0
                else:
                    # No cache at all, fetch fresh data
                    user_data = fetcher.fetch_user_data(username)
                    stats = fetcher.fetch_user_stats(username, user_data)
                    cache_manager.cache_user_data(username, user_data, stats)
            # else: fresh cache available, proceed to display

        # Display the results
        formatter.display(username, user_data, stats, spaced=spaced)

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _prompt_username() -> Optional[str]:
    """Prompt user for username if not provided."""
    try:
        username = input("Enter username: ").strip()
        return username if username else None
    except (KeyboardInterrupt, EOFError):
        print()
        return None


def _prompt_provider() -> Optional[str]:
    """Prompt user for git provider with interactive selection."""
    providers = [
        ('github', 'GitHub'),
        ('gitlab', 'GitLab'),
        ('gitea', 'Gitea/Forgejo/Codeberg'),
        ('sourcehut', 'Sourcehut')
    ]

    selected = 0

    try:
        while True:
            # Clear screen and print header
            print("\033[2J\033[H", end="")
            print("Choose your git provider:")
            print()

            # Print options with cursor
            for i, (key, name) in enumerate(providers):
                indicator = "●" if i == selected else "○"
                print(f"{indicator} {name}")

            print()
            print("Use ↑/↓ arrows, ● = selected, Enter to confirm")

            # Read key
            key = readchar.readkey()

            if key == readchar.key.UP:
                selected = (selected - 1) % len(providers)
            elif key == readchar.key.DOWN:
                selected = (selected + 1) % len(providers)
            elif key == readchar.key.ENTER:
                print()  # New line after selection
                return providers[selected][0]

    except (KeyboardInterrupt, EOFError):
        print()
        return None


def _create_fetcher(provider: str, base_url: str):
    """Create the appropriate fetcher for the provider."""
    if provider == 'github':
        from .fetcher import GitHubFetcher
        return GitHubFetcher()
    elif provider == 'gitlab':
        from .fetcher import GitLabFetcher
        return GitLabFetcher(base_url)
    elif provider == 'gitea':
        from .fetcher import GiteaFetcher
        return GiteaFetcher(base_url)
    elif provider == 'sourcehut':
        from .fetcher import SourcehutFetcher
        return SourcehutFetcher(base_url)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def _initialize_gitfetch(config_manager: ConfigManager) -> bool:
    """
    Initialize gitfetch by creating config directory and setting
    the authenticated user as default.

    Args:
        config_manager: ConfigManager instance

    Returns:
        True if initialization succeeded, False otherwise
    """
    try:
        # Ask user for git provider
        provider = _prompt_provider()
        if not provider:
            return False

        config_manager.set_provider(provider)

        # Set default URL for known providers
        if provider == 'github':
            config_manager.set_provider_url('https://api.github.com')
        elif provider == 'gitlab':
            config_manager.set_provider_url('https://gitlab.com')
        elif provider == 'gitea':
            url = input("Enter Gitea/Forgejo/Codeberg URL: ").strip()
            if not url:
                print("Provider URL required", file=sys.stderr)
                return False
            config_manager.set_provider_url(url)
        elif provider == 'sourcehut':
            config_manager.set_provider_url('https://git.sr.ht')

        # Create appropriate fetcher
        fetcher = _create_fetcher(provider, config_manager.get_provider_url())

        # Try to get authenticated user
        try:
            username = fetcher.get_authenticated_user()
            print(f"Using authenticated user: {username}")
        except Exception as e:
            print(f"Could not get authenticated user: {e}")
            if provider == 'github':
                print("Please authenticate with: gh auth login")
            elif provider == 'gitlab':
                print("Please authenticate with: glab auth login")
            else:
                print("Please ensure you have a valid token configured")
            return False

        # Save configuration
        config_manager.set_default_username(username)
        config_manager.save()

        return True

    except Exception as e:
        print(f"Error during initialization: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())
