"""
Git data fetcher for various git hosting providers
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import subprocess
import json
import sys
import os
import re


class BaseFetcher(ABC):
    """Abstract base class for git hosting provider fetchers."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the fetcher.

        Args:
            token: Optional authentication token
        """
        self.token = token

    @abstractmethod
    def get_authenticated_user(self) -> str:
        """
        Get the authenticated username.

        Returns:
            The login of the authenticated user
        """
        pass

    @abstractmethod
    def fetch_user_data(self, username: str) -> Dict[str, Any]:
        """
        Fetch basic user profile data.

        Args:
            username: Username to fetch data for

        Returns:
            Dictionary containing user profile data
        """
        pass

    @abstractmethod
    def fetch_user_stats(self, username: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch detailed statistics for a user.

        Args:
            username: Username to fetch stats for
            user_data: Optional pre-fetched user data

        Returns:
            Dictionary containing user statistics
        """
        pass

    @staticmethod
    def _build_contribution_graph_from_git(repo_path: str = ".") -> list:
        """
        Build contribution graph from local .git history.

        Args:
            repo_path: Path to the git repository (default: current dir)

        Returns:
            List of weeks with contribution data
        """
        from datetime import datetime, timedelta
        import collections

        try:
            # Get commit dates
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%ai', '--all'],
                capture_output=True, text=True, cwd=repo_path
            )
            if result.returncode != 0:
                return []

            commits = result.stdout.strip().split('\n')
            if not commits or commits == ['']:
                return []

            # Parse dates and count commits per day
            commit_counts = collections.Counter()
            for commit in commits:
                if commit:
                    date_str = commit.split(' ')[0]  # YYYY-MM-DD
                    commit_counts[date_str] += 1

            # Get date range (last year)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)

            # Build weeks
            weeks = []
            current_date = start_date
            while current_date <= end_date:
                week = {'contributionDays': []}
                for i in range(7):
                    day_date = current_date + timedelta(days=i)
                    if day_date > end_date:
                        break
                    count = commit_counts.get(day_date.isoformat(), 0)
                    week['contributionDays'].append({
                        'contributionCount': count,
                        'date': day_date.isoformat()
                    })
                if week['contributionDays']:
                    weeks.append(week)
                current_date += timedelta(days=7)

            return weeks

        except Exception:
            return []


class GitHubFetcher(BaseFetcher):
    """Fetches GitHub user data and statistics using GitHub CLI."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub fetcher.

        Args:
            token: Optional GitHub personal access token (ignored, uses gh CLI)
        """
        pass

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

    def get_authenticated_user(self) -> str:
        """
        Get the authenticated username.

        Returns:
            The login of the authenticated user
        """
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status', '--json', 'hosts'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                try:
                    yml = open(os.path.expanduser(
                        "~/.config/gh/hosts.yml"), 'r').read()
                    user = re.findall(" +user: +(.*)", yml)
                    if len(user) != 0:
                        return user[0]
                    else:
                        raise Exception("Failed to get auth status")
                except FileNotFoundError:
                    raise Exception("Failed to get auth status")

            data = json.loads(result.stdout)
            hosts = data.get('hosts', {})
            github_com = hosts.get('github.com', [])
            if github_com and len(github_com) > 0:
                return github_com[0]['login']
            else:
                raise Exception("No GitHub.com auth found")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            raise Exception("Could not determine authenticated user")

    def _gh_api(self, endpoint: str, method: str = "GET") -> Any:
        """
        Call GitHub API using gh CLI.

        Args:
            endpoint: API endpoint (e.g., '/users/octocat')
            method: HTTP method

        Returns:
            Parsed JSON response
        """
        self._check_gh_cli()
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
        self._check_gh_cli()
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
        self._check_gh_cli()
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
        from collections import defaultdict

        # First pass: collect all language occurrences with their casing
        language_occurrences: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int))

        for repo in repos:
            language = repo.get('language')
            if language:
                # Group by lowercase name, but keep track of different casings
                normalized = language.lower()
                language_occurrences[normalized][language] += 1

        # Second pass: choose canonical casing (most frequent) and sum counts
        language_counts: Dict[str, int] = {}

        for normalized, casings in language_occurrences.items():
            # Find the most common casing
            canonical_name = max(casings.items(), key=lambda x: x[1])[0]
            # Sum all occurrences for this language
            total_count = sum(casings.values())
            language_counts[canonical_name] = total_count

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
            # Determine search type based on query
            search_type = 'prs' if 'is:pr' in query else 'issues'

            # Remove is:pr/issue from query as it's implied by search type
            query = query.replace('is:pr ', '').replace('is:issue ', '')

            # Parse query string and convert to command-line flags
            flags = self._parse_search_query(query)

            # Build command with proper flags
            cmd = ['gh', 'search', search_type] + flags + [
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
                    # For prs search, we don't need this flag
                    # For issues search, is:issue is default
                    pass
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


class GitLabFetcher(BaseFetcher):
    """Fetches GitLab user data and statistics."""

    def __init__(self, base_url: str = "https://gitlab.com",
                 token: Optional[str] = None):
        """
        Initialize the GitLab fetcher.

        Args:
            base_url: GitLab instance base URL
            token: Optional GitLab personal access token
        """
        super().__init__(token)
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v4"

    def _check_glab_cli(self) -> None:
        """Check if GitLab CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ['glab', 'auth', 'status'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                print("GitLab CLI not authenticated", file=sys.stderr)
                print("Please run: glab auth login", file=sys.stderr)
                sys.exit(1)
        except FileNotFoundError:
            print("GitLab CLI (glab) not installed", file=sys.stderr)
            print("Install: https://gitlab.com/gitlab-org/cli",
                  file=sys.stderr)
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("Error: glab CLI timeout", file=sys.stderr)
            sys.exit(1)

    def get_authenticated_user(self) -> str:
        """
        Get the authenticated GitLab username.

        Returns:
            The username of the authenticated user
        """
        try:
            result = subprocess.run(
                ['glab', 'api', '/user'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise Exception("Failed to get user info")

            data = json.loads(result.stdout)
            return data.get('username', '')
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            raise Exception("Could not determine authenticated user")

    def _api_request(self, endpoint: str) -> Any:
        """
        Make API request to GitLab.

        Args:
            endpoint: API endpoint

        Returns:
            Parsed JSON response
        """
        cmd = ['glab', 'api', endpoint]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise Exception(f"API request failed: {result.stderr}")
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            raise Exception("GitLab API request timed out")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse API response: {e}")

    def fetch_user_data(self, username: str) -> Dict[str, Any]:
        """
        Fetch basic user profile data from GitLab.

        Args:
            username: GitLab username

        Returns:
            Dictionary containing user profile data
        """
        return self._api_request(f'/users?username={username}')[0]

    def fetch_user_stats(self, username: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch detailed statistics for a GitLab user.

        Args:
            username: GitLab username
            user_data: Optional pre-fetched user data

        Returns:
            Dictionary containing user statistics
        """
        if not user_data:
            user_data = self.fetch_user_data(username)

        user_id = user_data.get('id')

        # Fetch user's projects
        repos = self._api_request(f'/users/{user_id}/projects')

        total_stars = sum(repo.get('star_count', 0) for repo in repos)
        total_forks = sum(repo.get('forks_count', 0) for repo in repos)

        # Calculate language stats
        languages = {}
        for repo in repos:
            lang = repo.get('language', 'Unknown')
            if lang in languages:
                languages[lang] += 1
            else:
                languages[lang] = 1

        # GitLab doesn't have contribution graphs like GitHub
        # Return simplified stats
        return {
            'total_stars': total_stars,
            'total_forks': total_forks,
            'total_repos': len(repos),
            'languages': languages,
            'contribution_graph': [],  # Not available
            'pull_requests': {'open': 0, 'awaiting_review': 0, 'mentions': 0},
            'issues': {'assigned': 0, 'created': 0, 'mentions': 0},
        }


class GiteaFetcher(BaseFetcher):
    """Fetches Gitea/Forgejo/Codeberg user data and statistics."""

    def __init__(self, base_url: str, token: Optional[str] = None):
        """
        Initialize the Gitea fetcher.

        Args:
            base_url: Gitea instance base URL (required)
            token: Optional Gitea personal access token
        """
        super().__init__(token)
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"

    def get_authenticated_user(self) -> str:
        """
        Get the authenticated Gitea username.

        Returns:
            The username of the authenticated user
        """
        if not self.token:
            raise Exception("Token required for Gitea authentication")

        try:
            import requests
            headers = {'Authorization': f'token {self.token}'}
            response = requests.get(
                f'{self.api_base}/user', headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('login', '')
        except Exception as e:
            raise Exception(f"Could not get authenticated user: {e}")

    def _api_request(self, endpoint: str) -> Any:
        """
        Make API request to Gitea.

        Args:
            endpoint: API endpoint

        Returns:
            Parsed JSON response
        """
        if not self.token:
            raise Exception("Token required for Gitea API")

        try:
            import requests
            headers = {'Authorization': f'token {self.token}'}
            response = requests.get(
                f'{self.api_base}{endpoint}', headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Gitea API request failed: {e}")

    def fetch_user_data(self, username: str) -> Dict[str, Any]:
        """
        Fetch basic user profile data from Gitea.

        Args:
            username: Gitea username

        Returns:
            Dictionary containing user profile data
        """
        return self._api_request(f'/users/{username}')

    def fetch_user_stats(self, username: str, user_data=None):
        """
        Fetch detailed statistics for a Gitea user.

        Args:
            username: Gitea username
            user_data: Optional pre-fetched user data

        Returns:
            Dictionary containing user statistics
        """
        if not user_data:
            user_data = self.fetch_user_data(username)

        # Fetch user's repositories
        repos = self._api_request(f'/users/{username}/repos')

        total_stars = sum(repo.get('stars_count', 0) for repo in repos)
        total_forks = sum(repo.get('forks_count', 0) for repo in repos)

        # Calculate language stats
        languages = {}
        for repo in repos:
            lang = repo.get('language', 'Unknown')
            if lang and lang in languages:
                languages[lang] += 1
            elif lang:
                languages[lang] = 1

        # Gitea doesn't have contribution graphs or PR/issue stats like GitHub
        return {
            'total_stars': total_stars,
            'total_forks': total_forks,
            'total_repos': len(repos),
            'languages': languages,
            'contribution_graph': [],  # Not available
            'pull_requests': {'open': 0, 'awaiting_review': 0, 'mentions': 0},
            'issues': {'assigned': 0, 'created': 0, 'mentions': 0},
        }


class SourcehutFetcher(BaseFetcher):
    """Fetches Sourcehut user data and statistics."""

    def __init__(self, base_url: str = "https://git.sr.ht", token: Optional[str] = None):
        """
        Initialize the Sourcehut fetcher.

        Args:
            base_url: Sourcehut instance base URL
            token: Optional Sourcehut personal access token
        """
        super().__init__(token)
        self.base_url = base_url.rstrip('/')

    def get_authenticated_user(self) -> str:
        """
        Get the authenticated Sourcehut username.

        Returns:
            The username of the authenticated user
        """
        if not self.token:
            raise Exception("Token required for Sourcehut authentication")

        # Sourcehut uses GraphQL API
        try:
            import requests
            query = """
            query {
                me {
                    username
                }
            }
            """
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.post(
                f'{self.base_url}/graphql',
                json={'query': query},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('me', {}).get('username', '')
        except Exception as e:
            raise Exception(f"Could not get authenticated user: {e}")

    def fetch_user_data(self, username: str) -> Dict[str, Any]:
        """
        Fetch basic user profile data from Sourcehut.

        Args:
            username: Sourcehut username

        Returns:
            Dictionary containing user profile data
        """
        # Sourcehut GraphQL query for user
        query = f"""
        query {{
            user(username: "{username}") {{
                username
                name
                bio
                location
                website
            }}
        }}
        """
        try:
            import requests
            headers = {
                'Authorization': f'Bearer {self.token}'} if self.token else {}
            response = requests.post(
                f'{self.base_url}/graphql',
                json={'query': query},
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('user', {})
        except Exception as e:
            raise Exception(f"Sourcehut API request failed: {e}")

    def fetch_user_stats(self, username: str, user_data=None):
        """
        Fetch detailed statistics for a Sourcehut user.

        Args:
            username: Sourcehut username
            user_data: Optional pre-fetched user data

        Returns:
            Dictionary containing user statistics
        """
        # Sourcehut has limited public stats, return minimal data
        return {
            'total_stars': 0,  # Not available
            'total_forks': 0,  # Not available
            'total_repos': 0,  # Would need separate API call
            'languages': {},  # Not available
            'contribution_graph': [],  # Not available
            'pull_requests': {'open': 0, 'awaiting_review': 0, 'mentions': 0},
            'issues': {'assigned': 0, 'created': 0, 'mentions': 0},
        }
