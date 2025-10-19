"""
GitHub data fetcher using the GitHub CLI (gh)
"""

from typing import Optional, Dict, Any
import subprocess
import json
import sys


class GitHubFetcher:
    """Fetches GitHub user data and statistics using GitHub CLI."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub fetcher.

        Args:
            token: Optional GitHub personal access token (ignored, uses gh CLI)
        """
        # Check if gh CLI is installed and authenticated
        self._check_gh_cli()

    def _check_gh_cli(self) -> None:
        """Check if GitHub CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                print("\n⚠️  GitHub CLI is not authenticated!", file=sys.stderr)
                print("Please run: gh auth login", file=sys.stderr)
                print("Then try gitfetch again.\n", file=sys.stderr)
                sys.exit(1)
        except FileNotFoundError:
            print("\n❌ GitHub CLI (gh) is not installed!", file=sys.stderr)
            print("\nInstall it with:", file=sys.stderr)
            print("  macOS: brew install gh", file=sys.stderr)
            print("  Linux: See https://github.com/cli/cli#installation",
                  file=sys.stderr)
            print("\nThen run: gh auth login", file=sys.stderr)
            print("And try gitfetch again.\n", file=sys.stderr)
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("Error: gh CLI command timed out", file=sys.stderr)
            sys.exit(1)

    def _gh_api(self, endpoint: str, method: str = "GET") -> Any:
        """
        Call GitHub API using gh CLI.

        Args:
            endpoint: API endpoint (e.g., '/users/octocat')
            method: HTTP method

        Returns:
            Parsed JSON response
        """
        try:
            result = subprocess.run(
                ['gh', 'api', endpoint, '-X', method],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise Exception(f"gh api failed: {result.stderr}")
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            raise Exception("GitHub API request timed out")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse GitHub API response: {e}")

    def fetch_user_data(self, username: str) -> Dict[str, Any]:
        """
        Fetch basic user profile data from GitHub.

        Args:
            username: GitHub username

        Returns:
            Dictionary containing user profile data
        """
        return self._gh_api(f'/users/{username}')

    def fetch_user_stats(self, username: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch detailed statistics for a GitHub user.

        Args:
            username: GitHub username
            user_data: Optional pre-fetched user data to avoid duplicate API call

        Returns:
            Dictionary containing user statistics
        """
        repos = self._fetch_repos(username)

        total_stars = sum(repo.get('stargazers_count', 0) for repo in repos)
        total_forks = sum(repo.get('forks_count', 0) for repo in repos)
        languages = self._calculate_language_stats(repos)

        # Fetch contribution graph
        contrib_graph = self._fetch_contribution_graph(username)

        # Use @me for search queries if this is the authenticated user
        search_username = self._get_search_username(username)

        pull_requests = {
            'awaiting_review': self._search_items(
                f'is:pr state:open review-requested:{search_username}'
            ),
            'open': self._search_items(
                f'is:pr state:open author:{search_username}'
            ),
            'mentions': self._search_items(
                f'is:pr state:open mentions:{search_username}'
            ),
        }

        issues = {
            'assigned': self._search_items(
                f'is:issue state:open assignee:{search_username}'
            ),
            'created': self._search_items(
                f'is:issue state:open author:{search_username}'
            ),
            'mentions': self._search_items(
                f'is:issue state:open mentions:{search_username}'
            ),
        }

        return {
            'total_stars': total_stars,
            'total_forks': total_forks,
            'total_repos': len(repos),
            'languages': languages,
            'contribution_graph': contrib_graph,
            'pull_requests': pull_requests,
            'issues': issues,
        }

    def _get_search_username(self, username: str) -> str:
        """
        Get the username to use for search queries.
        Uses @me for the authenticated user, otherwise the provided username.

        Args:
            username: The username to check

        Returns:
            Username for search queries (@me or the actual username)
        """
        try:
            # Get the authenticated user's login
            auth_user = self._gh_api('/user')
            if auth_user.get('login') == username:
                return '@me'
        except Exception:
            # If we can't determine auth user, use provided username
            pass
        return username

    def _fetch_repos(self, username: str) -> list:
        """
        Fetch all public repositories for a user.

        Args:
            username: GitHub username

        Returns:
            List of repository data
        """
        repos = []
        page = 1
        per_page = 100

        while True:
            endpoint = (
                f'/users/{username}/repos?page={page}'
                f'&per_page={per_page}&type=owner&sort=updated'
            )
            data = self._gh_api(endpoint)

            if not data:
                break

            repos.extend(data)
            page += 1

            # Stop if we got less than a full page
            if len(data) < per_page:
                break

        return repos

    def _calculate_language_stats(self, repos: list) -> Dict[str, float]:
        """
        Calculate language usage statistics from repositories.

        Args:
            repos: List of repository data

        Returns:
            Dictionary mapping language names to percentages
        """
        language_counts: Dict[str, int] = {}

        for repo in repos:
            language = repo.get('language')
            if language:
                language_counts[language] = language_counts.get(
                    language, 0) + 1

        # Calculate percentages
        total = sum(language_counts.values())
        if total == 0:
            return {}

        language_percentages = {
            lang: (count / total) * 100
            for lang, count in language_counts.items()
        }

        return language_percentages

    def _search_items(self, query: str, per_page: int = 5) -> Dict[str, Any]:
        """Search issues and PRs using GitHub CLI search command."""
        try:
            # Parse query string and convert to command-line flags
            flags = self._parse_search_query(query)

            # Build command with proper flags
            cmd = ['gh', 'search', 'issues'] + flags + [
                '--limit', str(per_page),
                '--json', 'number,title,repository,url,state'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return {'total_count': 0, 'items': []}

            data = json.loads(result.stdout)
            items = []
            for item in data[:per_page]:
                repo_info = item.get('repository', {})
                repo_name = repo_info.get(
                    'nameWithOwner',
                    repo_info.get('name', '')
                )
                items.append({
                    'title': item.get('title', ''),
                    'repo': repo_name,
                    'url': item.get('url', ''),
                    'number': item.get('number')
                })

            # gh search doesn't return total count in JSON, use item count
            return {
                'total_count': len(items),
                'items': items
            }
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return {'total_count': 0, 'items': []}

    def _parse_search_query(self, query: str) -> list:
        """Parse search query string into command-line flags."""
        flags = []
        parts = query.split()

        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                if key == 'assignee':
                    flags.extend(['--assignee', value])
                elif key == 'author':
                    flags.extend(['--author', value])
                elif key == 'mentions':
                    flags.extend(['--mentions', value])
                elif key == 'review-requested':
                    flags.extend(['--review-requested', value])
                elif key == 'state':
                    flags.extend(['--state', value])
                elif key == 'is':
                    # Handle is:pr and is:issue
                    if value == 'pr':
                        flags.append('--include-prs')
                    # is:issue is default, no flag needed
                else:
                    # For other qualifiers, add as search term
                    flags.append(part)
            else:
                # Add as general search term
                flags.append(part)

        return flags

    @staticmethod
    def _extract_repo_name(repo_url: str) -> str:
        """Extract owner/repo from a repository API URL."""
        if not repo_url:
            return ""

        parts = repo_url.rstrip('/').split('/')
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return repo_url

    def _get_rate_limit(self) -> Dict[str, Any]:
        """
        Check current GitHub API rate limit status.

        Returns:
            Dictionary containing rate limit info
        """
        return self._gh_api('/rate_limit')

    def _fetch_contribution_graph(self, username: str) -> list:
        """
        Fetch contribution graph data using GraphQL.

        Args:
            username: GitHub username

        Returns:
            List of weeks with contribution data
        """
        # GraphQL query for contribution calendar (inline username)
        query = f'''{{
          user(login: "{username}") {{
            contributionsCollection {{
              contributionCalendar {{
                weeks {{
                  contributionDays {{
                    contributionCount
                    date
                  }}
                }}
              }}
            }}
          }}
        }}'''

        try:
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            data = json.loads(result.stdout)
            weeks = data.get('data', {}).get('user', {}).get(
                'contributionsCollection', {}).get(
                    'contributionCalendar', {}).get('weeks', [])
            return weeks

        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return []
