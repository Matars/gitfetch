"""
Git data fetcher for various git hosting providers
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, TypeVar
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
import subprocess
import json
import logging
import sys
import os
import re
import time

from .constants import (
    API_TIMEOUT_SHORT,
    API_TIMEOUT_MEDIUM,
    API_TIMEOUT_LONG,
    SEARCH_RESULTS_PER_PAGE,
    REPOS_PER_PAGE,
    RATE_LIMIT_WARNING_THRESHOLD,
    RATE_LIMIT_CRITICAL_THRESHOLD,
)
from .exceptions import (
    AuthenticationError,
    APIError,
    RateLimitError,
    UserNotFoundError,
    redact_sensitive_info,
)
from .calculations import (
    calculate_current_streak,
    calculate_max_streak,
    calculate_total_contributions,
    calculate_streaks,
    calculate_language_percentages,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_on_failure(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_multiplier, max_delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception  # type: ignore

        return wrapper

    return decorator


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
    def fetch_user_stats(
        self, username: str, user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
                ["git", "log", "--pretty=format:%ai", "--all"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            if result.returncode != 0:
                return []

            commits = result.stdout.strip().split("\n")
            if not commits or commits == [""]:
                return []

            # Parse dates and count commits per day
            commit_counts: collections.Counter[str] = collections.Counter()
            for commit in commits:
                if commit:
                    date_str = commit.split(" ")[0]  # YYYY-MM-DD
                    commit_counts[date_str] += 1

            # Get date range (last year)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)

            # Build weeks
            weeks: list[dict[str, Any]] = []
            current_date = start_date
            while current_date <= end_date:
                week: dict[str, Any] = {"contributionDays": []}
                for i in range(7):
                    day_date = current_date + timedelta(days=i)
                    if day_date > end_date:
                        break
                    count = commit_counts.get(day_date.isoformat(), 0)
                    week["contributionDays"].append(
                        {"contributionCount": count, "date": day_date.isoformat()}
                    )
                if week["contributionDays"]:
                    weeks.append(week)
                current_date += timedelta(days=7)

            return weeks

        except Exception as e:
            logger.debug(f"Failed to build contribution graph from git: {e}")
            return []


class GitHubFetcher(BaseFetcher):
    """Fetches GitHub user data and statistics using GitHub CLI."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub fetcher.

        Args:
            token: Optional GitHub personal access token
        """
        super().__init__(token)

    def _build_env(self) -> dict:
        """
        Build environment dict with token if available.

        Returns:
            Environment dict for subprocess calls
        """
        env = os.environ.copy()
        if self.token:
            env["GH_TOKEN"] = self.token
        return env

    def _check_gh_cli(self) -> None:
        """Check if GitHub CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_SHORT,
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
            print(
                "  Linux: See https://github.com/cli/cli#installation", file=sys.stderr
            )
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
                ["gh", "auth", "status", "--json", "hosts"],
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_SHORT,
            )
            if result.returncode != 0:
                try:
                    with open(os.path.expanduser("~/.config/gh/hosts.yml"), "r") as f:
                        yml = f.read()
                    user = re.findall(" +user: +(.*)", yml)
                    if len(user) != 0:
                        return user[0]
                    else:
                        raise AuthenticationError("Failed to get authentication status")
                except FileNotFoundError:
                    raise AuthenticationError("Failed to get authentication status")

            data = json.loads(result.stdout)
            hosts = data.get("hosts", {})
            github_com = hosts.get("github.com", [])
            if github_com and len(github_com) > 0:
                return github_com[0]["login"]
            else:
                raise Exception("No GitHub.com auth found")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            raise Exception("Could not determine authenticated user")

    @retry_on_failure(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(subprocess.TimeoutExpired, json.JSONDecodeError, OSError),
    )
    def _gh_api(self, endpoint: str, method: str = "GET") -> Any:
        """
        Call GitHub API using gh CLI.

        Retries on timeout, network errors, and JSON parsing failures.

        Args:
            endpoint: API endpoint (e.g., '/users/octocat')
            method: HTTP method

        Returns:
            Parsed JSON response
        """
        self._check_gh_cli()
        try:
            result = subprocess.run(
                ["gh", "api", endpoint, "-X", method],
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_LONG,
                env=self._build_env(),
            )
            if result.returncode != 0:
                raise APIError(
                    f"GitHub API failed: {result.stderr}",
                    hint="Check your authentication token",
                )
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            raise APIError(
                "GitHub API request timed out", hint="Check your network connection"
            )
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse GitHub API response: {e}")

    def _check_rate_limit_status(self) -> None:
        """
        Check GitHub API rate limit status and warn if approaching limits.

        Uses the /rate_limit endpoint to get current quota status.
        """
        try:
            rate_data = self._gh_api("/rate_limit")
            # GitHub API rate limit structure
            core = rate_data.get("resources", {}).get("core", {})
            remaining = core.get("remaining", 0)
            limit = core.get("limit", 5000)
            used = limit - remaining

            if limit > 0:
                usage_percent = (used / limit) * 100
                if usage_percent >= RATE_LIMIT_CRITICAL_THRESHOLD:
                    logger.warning(
                        f"GitHub API rate limit critical: {used}/{limit} used ({usage_percent:.0f}%)"
                    )
                elif usage_percent >= RATE_LIMIT_WARNING_THRESHOLD:
                    logger.warning(
                        f"GitHub API rate limit warning: {used}/{limit} used ({usage_percent:.0f}%)"
                    )
        except Exception:
            # Don't fail if rate limit check fails
            pass

    def fetch_user_data(self, username: str) -> Dict[str, Any]:
        """
        Fetch basic user profile data from GitHub.

        Args:
            username: GitHub username

        Returns:
            Dictionary containing user profile data
        """
        self._check_gh_cli()
        return self._gh_api(f"/users/{username}")

    def fetch_user_stats(
        self, username: str, user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetch detailed statistics for a GitHub user.

        Uses parallel execution to fetch independent data concurrently.

        Args:
            username: GitHub username
            user_data: Optional pre-fetched user data to avoid duplicate API call

        Returns:
            Dictionary containing user statistics
        """
        self._check_gh_cli()

        # Check rate limit status before making many API calls
        self._check_rate_limit_status()

        # Fetch independent data in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit initial parallel tasks
            future_repos = executor.submit(self._fetch_repos, username)
            future_contrib_graph = executor.submit(
                self._fetch_contribution_graph, username
            )
            future_search_username = executor.submit(
                self._get_search_username, username
            )

            # Wait for repos to complete (needed for star/fork/language stats)
            repos = future_repos.result()
            contrib_graph = future_contrib_graph.result()
            search_username = future_search_username.result()

            # Calculate stats that depend on repos
            total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
            total_forks = sum(repo.get("forks_count", 0) for repo in repos)
            languages = self._calculate_language_stats(repos)

            # Calculate current contribution streak and total contributions
            current_streak = self._calculate_current_streak(contrib_graph)
            total_contributions = self._calculate_total_contributions(contrib_graph)

            # Submit all search queries in parallel
            future_pr_awaiting = executor.submit(
                self._search_items,
                f"is:pr state:open review-requested:{search_username}",
            )
            future_pr_open = executor.submit(
                self._search_items, f"is:pr state:open author:{search_username}"
            )
            future_pr_mentions = executor.submit(
                self._search_items, f"is:pr state:open mentions:{search_username}"
            )
            future_pr_draft = executor.submit(
                self._search_items, f"is:pr is:draft author:{search_username}"
            )
            future_pr_merged = executor.submit(
                self._search_items, f"is:pr is:merged author:{search_username}"
            )
            # PRs closed in the last 30 days
            from datetime import datetime, timedelta

            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            future_pr_closed_recently = executor.submit(
                self._search_items,
                f"is:pr is:closed author:{search_username} closed:>={thirty_days_ago}",
            )
            future_issue_assigned = executor.submit(
                self._search_items, f"is:issue state:open assignee:{search_username}"
            )
            future_issue_created = executor.submit(
                self._search_items, f"is:issue state:open author:{search_username}"
            )
            future_issue_mentions = executor.submit(
                self._search_items, f"is:issue state:open mentions:{search_username}"
            )
            future_issue_commented = executor.submit(
                self._search_items, f"is:issue commenter:{search_username} state:open"
            )

            # Collect all PR and issue results
            pull_requests = {
                "awaiting_review": future_pr_awaiting.result(),
                "open": future_pr_open.result(),
                "mentions": future_pr_mentions.result(),
                "draft": future_pr_draft.result(),
                "merged": future_pr_merged.result(),
                "closed_recently": future_pr_closed_recently.result(),
            }
            issues = {
                "assigned": future_issue_assigned.result(),
                "created": future_issue_created.result(),
                "mentions": future_issue_mentions.result(),
                "commented": future_issue_commented.result(),
            }

        return {
            "total_stars": total_stars,
            "total_forks": total_forks,
            "total_repos": len(repos),
            "languages": languages,
            "contribution_graph": contrib_graph,
            "current_streak": current_streak,
            "max_streak": self._calculate_max_streak(contrib_graph),
            "total_contributions": total_contributions,
            "pull_requests": pull_requests,
            "issues": issues,
        }

    def _calculate_current_streak(self, contrib_graph: list) -> int:
        """
        Calculate the current contribution streak from contribution graph.

        Args:
            contrib_graph: List of weeks with contribution data

        Returns:
            Current streak of consecutive days with contributions
        """
        return calculate_current_streak(contrib_graph)

    def _calculate_max_streak(self, contrib_graph: list) -> int:
        """
        Calculate the maximum (best) contribution streak from contribution graph.

        Args:
            contrib_graph: List of weeks with contribution data

        Returns:
            Maximum streak of consecutive days with contributions
        """
        return calculate_max_streak(contrib_graph)

    def _calculate_total_contributions(self, contrib_graph: list) -> int:
        """
        Calculate total contributions from contribution graph.

        Args:
            contrib_graph: List of weeks with contribution data

        Returns:
            Total contributions across all weeks
        """
        return calculate_total_contributions(contrib_graph)

    def _calculate_max_streak(self, contrib_graph: list) -> int:
        """
        Calculate the maximum (best) contribution streak from contribution graph.

        Args:
            contrib_graph: List of weeks with contribution data

        Returns:
            Maximum streak of consecutive days with contributions
        """
        try:
            all_contributions = []
            for week in contrib_graph:
                for day in week.get("contributionDays", []):
                    all_contributions.append(day.get("contributionCount", 0))

            # Keep chronological order for max streak calculation
            max_streak = 0
            temp_streak = 0
            for contrib in all_contributions:
                if contrib > 0:
                    temp_streak += 1
                    if temp_streak > max_streak:
                        max_streak = temp_streak
                else:
                    temp_streak = 0
            return max_streak
        except Exception:
            return 0

    def _calculate_total_contributions(self, contrib_graph: list) -> int:
        """
        Calculate total contributions from contribution graph.

        Args:
            contrib_graph: List of weeks with contribution data

        Returns:
            Total contributions across all weeks
        """
        try:
            total = 0
            for week in contrib_graph:
                for day in week.get("contributionDays", []):
                    total += day.get("contributionCount", 0)
            return total
        except Exception:
            return 0

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
            auth_user = self._gh_api("/user")
            if auth_user.get("login") == username:
                return "@me"
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
        per_page = REPOS_PER_PAGE

        while True:
            endpoint = (
                f"/users/{username}/repos?page={page}"
                f"&per_page={per_page}&type=owner&sort=updated"
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

        Uses GitHub API to fetch actual code size (bytes) for each language
        across all repositories, providing accurate percentages.

        Args:
            repos: List of repository data

        Returns:
            Dictionary mapping language names to percentages
        """
        from collections import defaultdict

        if not repos:
            return {}

        # Aggregate language bytes across all repositories
        language_bytes: Dict[str, int] = defaultdict(int)

        # Fetch detailed language stats for each repo in parallel
        # Limit to 50 repos to avoid excessive API calls/rate limits
        repos_to_analyze = repos[:50]

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_languages = {
                executor.submit(self._fetch_repo_languages, repo): repo
                for repo in repos_to_analyze
            }

            for future in future_languages:
                try:
                    repo_languages = future.result(timeout=API_TIMEOUT_MEDIUM)
                    for lang, bytes_count in repo_languages.items():
                        language_bytes[lang] += bytes_count
                except Exception:
                    # If we can't get detailed stats, fall back to basic language
                    repo = future_languages[future]
                    basic_lang = repo.get("language")
                    if basic_lang:
                        # Assign a small default weight for repos without detailed stats
                        language_bytes[basic_lang] += 1

        # Calculate percentages using centralized calculation function
        return calculate_language_percentages(language_bytes)

    def _fetch_repo_languages(self, repo: dict) -> Dict[str, int]:
        """
        Fetch detailed language statistics for a single repository.

        Args:
            repo: Repository data dictionary

        Returns:
            Dictionary mapping language names to byte counts
        """
        try:
            owner = repo.get("owner", {}).get("login")
            repo_name = repo.get("name")
            if not owner or not repo_name:
                return {}

            endpoint = f"/repos/{owner}/{repo_name}/languages"
            data = self._gh_api(endpoint)
            return data if data else {}
        except Exception:
            return {}

    def _search_items(
        self, query: str, per_page: int = SEARCH_RESULTS_PER_PAGE
    ) -> Dict[str, Any]:
        """
        Search issues and PRs using GitHub Search REST API.

        Uses REST API instead of CLI search to get accurate total_count.
        Retries on timeout and network errors.

        Args:
            query: Search query string
            per_page: Number of results to return

        Returns:
            Dictionary with total_count (accurate) and items list
        """
        try:
            # URL encode the query
            from urllib.parse import quote

            encoded_query = quote(query)

            # Use GitHub Search API - returns accurate total_count
            # The /search/issues endpoint returns both issues and PRs
            endpoint = f"/search/issues?q={encoded_query}&per_page={per_page}"

            data = self._gh_api(endpoint)

            items = []
            for item in data.get("items", [])[:per_page]:
                repo_info = item.get("repository", {})
                repo_name = repo_info.get("full_name", "")
                items.append(
                    {
                        "title": item.get("title", ""),
                        "repo": repo_name,
                        "url": item.get("html_url", ""),
                        "number": item.get("number"),
                        "state": item.get("state", ""),
                    }
                )

            # REST API returns accurate total_count
            total_count = data.get("total_count", 0)

            return {"total_count": total_count, "items": items}
        except Exception:
            # Return empty result on any error after retries
            return {"total_count": 0, "items": []}

    @staticmethod
    def _extract_repo_name(repo_url: str) -> str:
        """Extract owner/repo from a repository API URL."""
        if not repo_url:
            return ""

        parts = repo_url.rstrip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return repo_url

    def _get_rate_limit(self) -> Dict[str, Any]:
        """
        Check current GitHub API rate limit status.

        Returns:
            Dictionary containing rate limit info
        """
        return self._gh_api("/rate_limit")

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
            contributionsCollection(includePrivate: true) {{
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
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_LONG,
                env=self._build_env(),
            )

            if result.returncode != 0:
                return []

            data = json.loads(result.stdout)
            weeks = (
                data.get("data", {})
                .get("user", {})
                .get("contributionsCollection", {})
                .get("contributionCalendar", {})
                .get("weeks", [])
            )
            return weeks

        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return []


class GitLabFetcher(BaseFetcher):
    """Fetches GitLab user data and statistics."""

    def __init__(
        self, base_url: str = "https://gitlab.com", token: Optional[str] = None
    ):
        """
        Initialize the GitLab fetcher.

        Args:
            base_url: GitLab instance base URL
            token: Optional GitLab personal access token
        """
        super().__init__(token)
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v4"

    def _build_env(self) -> dict:
        """
        Build environment dict with token if available.

        Returns:
            Environment dict for subprocess calls
        """
        env = os.environ.copy()
        if self.token:
            env["GITLAB_TOKEN"] = self.token
        return env

    def _check_glab_cli(self) -> None:
        """Check if GitLab CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["glab", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_SHORT,
            )
            if result.returncode != 0:
                print("GitLab CLI not authenticated", file=sys.stderr)
                print("Please run: glab auth login", file=sys.stderr)
                sys.exit(1)
        except FileNotFoundError:
            print("GitLab CLI (glab) not installed", file=sys.stderr)
            print("Install: https://gitlab.com/gitlab-org/cli", file=sys.stderr)
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
                ["glab", "api", "/user"],
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_MEDIUM,
                env=self._build_env(),
            )
            if result.returncode != 0:
                raise Exception("Failed to get user info")

            data = json.loads(result.stdout)
            return data.get("username", "")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            raise Exception("Could not determine authenticated user")

    @retry_on_failure(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(subprocess.TimeoutExpired, json.JSONDecodeError, OSError),
    )
    def _api_request(self, endpoint: str) -> Any:
        """
        Make API request to GitLab.

        Retries on timeout, network errors, and JSON parsing failures.

        Args:
            endpoint: API endpoint

        Returns:
            Parsed JSON response
        """
        cmd = ["glab", "api", endpoint]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_LONG,
                env=self._build_env(),
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
        return self._api_request(f"/users?username={username}")[0]

    def fetch_user_stats(
        self, username: str, user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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

        user_id = user_data.get("id")

        # Fetch user's projects
        repos = self._api_request(f"/users/{user_id}/projects")

        total_stars = sum(repo.get("star_count", 0) for repo in repos)
        total_forks = sum(repo.get("forks_count", 0) for repo in repos)

        # Calculate language stats
        languages: dict[str, int] = {}
        for repo in repos:
            lang = repo.get("language", "Unknown")
            if lang in languages:
                languages[lang] += 1
            else:
                languages[lang] = 1

        # GitLab doesn't have contribution graphs like GitHub
        # Return simplified stats
        return {
            "total_stars": total_stars,
            "total_forks": total_forks,
            "total_repos": len(repos),
            "languages": languages,
            "contribution_graph": [],  # Not available
            "total_contributions": 0,  # Not available without contribution graph
            "pull_requests": {
                "open": 0,
                "awaiting_review": 0,
                "mentions": 0,
                "draft": 0,
                "merged": 0,
                "closed_recently": 0,
            },
            "issues": {
                "assigned": 0,
                "created": 0,
                "mentions": 0,
                "commented": 0,
            },
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
        self.base_url = base_url.rstrip("/")
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

            headers = {"Authorization": f"token {self.token}"}
            response = requests.get(
                f"{self.api_base}/user", headers=headers, timeout=API_TIMEOUT_MEDIUM
            )
            response.raise_for_status()
            data = response.json()
            return data.get("login", "")
        except Exception as e:
            # Redact token from error message
            error_msg = redact_sensitive_info(str(e), [self.token] if self.token else None)
            raise Exception(f"Could not get authenticated user: {error_msg}")

    @retry_on_failure(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(OSError,),  # Will catch requests errors wrapped in Exception
    )
    def _api_request(self, endpoint: str) -> Any:
        """
        Make API request to Gitea.

        Retries on network errors and timeouts.

        Args:
            endpoint: API endpoint

        Returns:
            Parsed JSON response
        """
        if not self.token:
            raise Exception("Token required for Gitea API")

        try:
            import requests

            headers = {"Authorization": f"token {self.token}"}
            response = requests.get(
                f"{self.api_base}{endpoint}", headers=headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Redact token from error message
            error_msg = redact_sensitive_info(str(e), [self.token] if self.token else None)
            raise Exception(f"Gitea API request failed: {error_msg}")

    def fetch_user_data(self, username: str) -> Dict[str, Any]:
        """
        Fetch basic user profile data from Gitea.

        Args:
            username: Gitea username

        Returns:
            Dictionary containing user profile data
        """
        return self._api_request(f"/users/{username}")

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
        repos = self._api_request(f"/users/{username}/repos")

        total_stars = sum(repo.get("stars_count", 0) for repo in repos)
        total_forks = sum(repo.get("forks_count", 0) for repo in repos)

        # Calculate language stats
        languages: dict[str, int] = {}
        for repo in repos:
            lang = repo.get("language", "Unknown")
            if lang and lang in languages:
                languages[lang] += 1
            elif lang:
                languages[lang] = 1

        # Gitea doesn't have contribution graphs or PR/issue stats like GitHub
        return {
            "total_stars": total_stars,
            "total_forks": total_forks,
            "total_repos": len(repos),
            "languages": languages,
            "contribution_graph": [],  # Not available
            "total_contributions": 0,  # Not available without contribution graph
            "pull_requests": {
                "open": 0,
                "awaiting_review": 0,
                "mentions": 0,
                "draft": 0,
                "merged": 0,
                "closed_recently": 0,
            },
            "issues": {
                "assigned": 0,
                "created": 0,
                "mentions": 0,
                "commented": 0,
            },
        }


class SourcehutFetcher(BaseFetcher):
    """Fetches Sourcehut user data and statistics."""

    def __init__(
        self, base_url: str = "https://git.sr.ht", token: Optional[str] = None
    ):
        """
        Initialize the Sourcehut fetcher.

        Args:
            base_url: Sourcehut instance base URL
            token: Optional Sourcehut personal access token
        """
        super().__init__(token)
        self.base_url = base_url.rstrip("/")

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
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{self.base_url}/graphql",
                json={"query": query},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("me", {}).get("username", "")
        except Exception as e:
            # Redact token from error message
            error_msg = redact_sensitive_info(str(e), [self.token] if self.token else None)
            raise Exception(f"Could not get authenticated user: {error_msg}")

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

            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.post(
                f"{self.base_url}/graphql",
                json={"query": query},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("user", {})
        except Exception as e:
            # Redact token from error message
            error_msg = redact_sensitive_info(str(e), [self.token] if self.token else None)
            raise Exception(f"Sourcehut API request failed: {error_msg}")

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
            "total_stars": 0,  # Not available
            "total_forks": 0,  # Not available
            "total_repos": 0,  # Would need separate API call
            "languages": {},  # Not available
            "contribution_graph": [],  # Not available
            "total_contributions": 0,  # Not available without contribution graph
            "pull_requests": {
                "open": 0,
                "awaiting_review": 0,
                "mentions": 0,
                "draft": 0,
                "merged": 0,
                "closed_recently": 0,
            },
            "issues": {
                "assigned": 0,
                "created": 0,
                "mentions": 0,
                "commented": 0,
            },
        }
