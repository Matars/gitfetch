"""
Command-line interface for gitfetch
"""

import argparse
import sys
import os
import subprocess
from typing import Optional

import readchar

from .display import DisplayFormatter
from .cache import CacheManager
from .config import ConfigManager
from . import __version__


def _background_refresh_cache_subprocess(username: str) -> None:
    """
    Background cache refresh function that runs as a standalone script.
    This is called by the subprocess, not directly.
    """
    try:
        # Re-create components
        config_manager = ConfigManager()
        cache_expiry = config_manager.get_cache_expiry_minutes()
        cache_manager = CacheManager(cache_expiry_minutes=cache_expiry)
        provider = config_manager.get_provider()
        provider_url = config_manager.get_provider_url()
        token = config_manager.get_token()
        fetcher = _create_fetcher(provider, provider_url, token)

        fresh_user_data = fetcher.fetch_user_data(username)
        fresh_stats = fetcher.fetch_user_stats(username, fresh_user_data)
        cache_manager.cache_user_data(username, fresh_user_data, fresh_stats)
    except Exception:
        # Silent fail - this is background refresh
        pass


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

    general_group = parser.add_argument_group('\033[92mGeneral Options\033[0m')
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
        "--version",
        action="store_true",
        help="Show version and check for updates"
    )

    general_group.add_argument(
        "--change-provider",
        action="store_true",
        help="Change the configured git provider"
    )

    # Hidden argument for background cache refresh
    general_group.add_argument(
        "--background-refresh",
        type=str,
        help=argparse.SUPPRESS  # Hide from help
    )

    general_group.add_argument(
        "--local",
        action="store_true",
        help="Fetch data specific to current local repo (requires .git folder)"
    )

    visual_group = parser.add_argument_group('\033[94mVisual Options\033[0m')
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
        "--graph-only",
        action="store_true",
        help="Show only the contribution graph"
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

    visual_group.add_argument(
        "--text",
        type=str,
        help="Display text as contribution graph pattern (simulation only)"
    )

    visual_group.add_argument(
        "--shape",
        nargs='+',
        help=("Display one or more predefined shapes as contribution graph "
              "(simulation only). Provide multiple shapes after the option: "
              "--shape kitty kitty")
    )

    visual_group.add_argument(
        "--graph-timeline",
        action="store_true",
        help="Show git timeline graph instead of contribution graph"
    )

    visibility_group = parser.add_argument_group('\033[95mVisibility\033[0m')
    visibility_group.add_argument(
        "--no-date",
        action="store_true",
        help="Hide month/date labels on contribution graph"
    )

    visibility_group.add_argument(
        "--no-achievements",
        action="store_true",
        help="Hide achievements section"
    )

    visibility_group.add_argument(
        "--no-languages",
        action="store_true",
        help="Hide languages section"
    )

    visibility_group.add_argument(
        "--no-issues",
        action="store_true",
        help="Hide issues section"
    )

    visibility_group.add_argument(
        "--no-pr",
        action="store_true",
        help="Hide pull requests section"
    )

    visibility_group.add_argument(
        "--no-account",
        action="store_true",
        help="Hide account information section"
    )

    visibility_group.add_argument(
        "--no-grid",
        action="store_true",
        help="Hide contribution grid/graph"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for gitfetch CLI."""
    try:
        args = parse_args()

        # Check for --local flag
        if args.local:
            if not os.path.exists('.git'):
                print("Error: --local requires .git folder", file=sys.stderr)
                return 1

        # Handle background refresh mode (hidden feature)
        if args.background_refresh:
            _background_refresh_cache_subprocess(args.background_refresh)
            return 0

        if args.change_provider:
            config_manager = ConfigManager()
            print("🔄 Changing git provider...\n")
            if not _initialize_gitfetch(config_manager):
                print("Error: Failed to change provider", file=sys.stderr)
                return 1
            print("\n✅ Provider changed successfully!")
            return 0

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
                            "Or run:\n"
                            "\t\tbrew update && brew upgrade gitfetch\033[0m")
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
        cache_expiry = config_manager.get_cache_expiry_minutes()
        cache_manager = CacheManager(cache_expiry_minutes=cache_expiry)
        provider = config_manager.get_provider()
        provider_url = config_manager.get_provider_url()
        token = config_manager.get_token()
        fetcher = _create_fetcher(provider, provider_url, token)

        # Handle custom box character
        custom_box = args.custom_box

        # Handle show date setting
        show_date = not args.no_date

        formatter = DisplayFormatter(
            config_manager,
            custom_box,
            show_date,
            args.graph_only,
            not args.no_achievements,
            not args.no_languages,
            not args.no_issues,
            not args.no_pr,
            not args.no_account,
            not args.no_grid,
            args.width,
            args.height,
            args.graph_timeline,
            args.local,
            args.shape,
            args.text,
        )
        if args.spaced:
            spaced = True
        elif args.not_spaced:
            spaced = False
        else:
            spaced = True

        # If --text or --shape provided, simulate contribution graph
        # and reuse cached metadata (issues, PRs, languages, achievements)
        if args.text or args.shape:
            if args.text and args.shape:
                print("Error: --text and --shape cannot be used together",
                      file=sys.stderr)
                return 1

            try:
                if args.text:
                    # Build a fake contribution_graph from the text
                    text_grid = formatter._text_to_grid(args.text)
                    weeks = formatter._generate_weeks_from_text_grid(text_grid)
                else:  # args.shape
                    # Use the predefined shape pattern (shape may be a list)
                    shape_grid = formatter._shape_to_grid(args.shape)
                    weeks = formatter._generate_weeks_from_text_grid(
                        shape_grid)
            except Exception as e:
                print(f"Error generating graph: {e}", file=sys.stderr)
                return 1

            # Try to reuse cached user metadata/stats when available
            lookup_username = args.username or config_manager.get_default_username()
            cached_user = None
            cached_stats = None
            if lookup_username:
                # Prefer fresh cache, but fall back to stale cache so
                # simulated graphs can still show metadata like streaks
                cached_user = (
                    cache_manager.get_cached_user_data(lookup_username)
                    or cache_manager.get_stale_cached_user_data(lookup_username)
                )
                cached_stats = (
                    cache_manager.get_cached_stats(lookup_username)
                    or cache_manager.get_stale_cached_stats(lookup_username)
                )

            if cached_stats:
                # Replace only the contribution graph with our simulated weeks
                cached_stats['contribution_graph'] = weeks
                stats = cached_stats
            else:
                stats = {'contribution_graph': weeks}

            if cached_user:
                user_data = cached_user
                display_name = cached_user.get('name') or lookup_username
            else:
                # Minimal fallback user_data for display purposes
                display_name = (
                    args.username
                    or (args.text if args.text else ' '.join(args.shape) if args.shape else None)
                )
                user_data = {
                    'name': display_name,
                    'bio': '',
                    'website': '',
                }

            formatter.display(
                display_name,
                user_data,
                stats,
                spaced=spaced,
            )
            return 0

        # Handle cache clearing
        if args.clear_cache:
            cache_manager.clear()
            print("Cache cleared successfully!")
            return 0

        # Get username
        username = (
            args.username
            or config_manager.get_default_username()
            or None
        )

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
            use_cache = not args.no_cache

            if use_cache:
                user_data = cache_manager.get_cached_user_data(username)
                stats = cache_manager.get_cached_stats(username)

                # If fresh cache is available, just display
                if user_data is not None and stats is not None:
                    formatter.display(username, user_data,
                                      stats, spaced=spaced)
                    return 0

                # Try stale cache for immediate display
                stale_user_data = cache_manager.get_stale_cached_user_data(
                    username)
                stale_stats = cache_manager.get_stale_cached_stats(username)

                if stale_user_data is not None and stale_stats is not None:
                    formatter.display(username, stale_user_data,
                                      stale_stats, spaced=spaced)

                    # Spawn a completely independent background process
                    # Spawn background refresh process
                    try:
                        subprocess.Popen(
                            [sys.executable, "-m", "gitfetch.cli",
                                "--background-refresh", username],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL,
                            start_new_session=True,  # detach from parent
                        )
                    except Exception:
                        # If subprocess fails, silently continue
                        pass

                    return 0

                # No cache at all so fall through to fresh fetch

            # Either no_cache or no valid cache so just fetch fresh data
            user_data = fetcher.fetch_user_data(username)
            stats = fetcher.fetch_user_stats(username, user_data)
            cache_manager.cache_user_data(username, user_data, stats)

            # Display the results
            formatter.display(username, user_data, stats, spaced=spaced)
            return 0

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130


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


def _create_fetcher(provider: str, base_url: str, token: Optional[str] = None):
    """Create the appropriate fetcher for the provider."""
    if provider == 'github':
        from .fetcher import GitHubFetcher
        return GitHubFetcher(token)
    elif provider == 'gitlab':
        from .fetcher import GitLabFetcher
        return GitLabFetcher(base_url, token)
    elif provider == 'gitea':
        from .fetcher import GiteaFetcher
        return GiteaFetcher(base_url, token)
    elif provider == 'sourcehut':
        from .fetcher import SourcehutFetcher
        return SourcehutFetcher(base_url, token)
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

        # Ask for token if needed
        token = None
        if provider in ['gitlab', 'gitea', 'sourcehut']:
            token_input = input(
                f"Enter your {provider} personal access token "
                "(optional, press Enter to skip): "
            ).strip()
            if token_input:
                token = token_input
                config_manager.set_token(token)

        # Create appropriate fetcher
        fetcher = _create_fetcher(
            provider, config_manager.get_provider_url(), token
        )

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

        # Ask for cache expiry time
        cache_expiry_input = input(
            "Cache expiry in minutes (default: 15, Enter for default): "
        ).strip()
        if cache_expiry_input:
            try:
                cache_expiry = int(cache_expiry_input)
                if cache_expiry < 1:
                    print("Cache expiry must be >= 1 min. Using default: 15")
                    cache_expiry = 15
                config_manager.set_cache_expiry_minutes(cache_expiry)
            except ValueError:
                print("Invalid input. Using default: 15 minutes.")
                config_manager.set_cache_expiry_minutes(15)
        else:
            config_manager.set_cache_expiry_minutes(15)

        # Save configuration
        config_manager.set_default_username(username)
        config_manager.save()

        return True

    except Exception as e:
        print(f"Error during initialization: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())
