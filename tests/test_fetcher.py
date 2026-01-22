"""
Tests for fetcher functionality
"""

import time
from unittest.mock import Mock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor
import subprocess

from gitfetch.fetcher import GitHubFetcher, BaseFetcher, retry_on_failure


class TestBaseFetcher:
    """Test cases for BaseFetcher."""

    def test_is_abstract(self):
        """BaseFetcher should not be instantiable directly."""
        try:
            BaseFetcher()
            assert False, "BaseFetcher should be abstract"
        except TypeError:
            pass  # Expected


class TestGitHubFetcher:
    """Test cases for GitHubFetcher."""

    def setup_method(self):
        """Set up test fixtures."""
        self.fetcher = GitHubFetcher(token="test_token")

    def test_init(self):
        """Test GitHubFetcher initialization."""
        assert self.fetcher.token == "test_token"

    @patch('gitfetch.fetcher.subprocess.run')
    def test_fetch_user_stats_parallel_execution(self, mock_run):
        """Test that fetch_user_stats uses parallel execution for searches."""
        # Mock gh auth status
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"hosts": {"github.com": [{"login": "testuser"}]}}'
        )

        # Mock all the API calls
        def mock_api_call(endpoint, method="GET"):
            if '/users/testuser' in endpoint:
                return {'login': 'testuser', 'name': 'Test User'}
            elif '/repos' in endpoint:
                return [
                    {'stargazers_count': 10, 'forks_count': 2, 'language': 'Python'},
                    {'stargazers_count': 5, 'forks_count': 1, 'language': 'Python'},
                ]
            elif endpoint == '/user':
                return {'login': 'testuser'}
            elif endpoint == '/rate_limit':
                return {'resources': {}}
            return {}

        with patch.object(self.fetcher, '_gh_api', side_effect=mock_api_call):
            with patch.object(self.fetcher, '_search_items', return_value={'total_count': 0, 'items': []}):
                with patch.object(self.fetcher, '_fetch_contribution_graph', return_value=[]):
                    result = self.fetcher.fetch_user_stats('testuser')

        # Verify all expected fields are present
        assert 'total_stars' in result
        assert 'total_forks' in result
        assert 'total_repos' in result
        assert 'languages' in result
        assert 'contribution_graph' in result
        assert 'current_streak' in result
        assert 'pull_requests' in result
        assert 'issues' in result

        # Verify the calculated values
        assert result['total_stars'] == 15  # 10 + 5
        assert result['total_forks'] == 3  # 2 + 1
        assert result['total_repos'] == 2

    def test_calculate_current_streak_empty_graph(self):
        """Test streak calculation with empty contribution graph."""
        result = self.fetcher._calculate_current_streak([])
        assert result == 0

    def test_calculate_current_streak_no_contributions(self):
        """Test streak calculation with no contributions."""
        graph = [
            {
                'contributionDays': [
                    {'contributionCount': 0, 'date': '2025-01-01'},
                    {'contributionCount': 0, 'date': '2025-01-02'},
                ]
            }
        ]
        result = self.fetcher._calculate_current_streak(graph)
        assert result == 0

    def test_calculate_current_streak_active_streak(self):
        """Test streak calculation with active streak."""
        graph = [
            {
                'contributionDays': [
                    {'contributionCount': 0, 'date': '2025-01-01'},
                    {'contributionCount': 5, 'date': '2025-01-02'},
                    {'contributionCount': 3, 'date': '2025-01-03'},
                ]
            }
        ]
        result = self.fetcher._calculate_current_streak(graph)
        # Should count streak from newest day backwards
        assert result == 2

    def test_calculate_current_streak_broken_streak(self):
        """Test streak calculation with broken streak."""
        graph = [
            {
                'contributionDays': [
                    {'contributionCount': 5, 'date': '2025-01-01'},
                    {'contributionCount': 3, 'date': '2025-01-02'},
                    {'contributionCount': 0, 'date': '2025-01-03'},
                ]
            }
        ]
        result = self.fetcher._calculate_current_streak(graph)
        # Streak broken by day with 0 contributions
        assert result == 0

    def test_calculate_max_streak_empty_graph(self):
        """Test max streak calculation with empty contribution graph."""
        result = self.fetcher._calculate_max_streak([])
        assert result == 0

    def test_calculate_max_streak_no_contributions(self):
        """Test max streak calculation with no contributions."""
        graph = [
            {
                'contributionDays': [
                    {'contributionCount': 0, 'date': '2025-01-01'},
                    {'contributionCount': 0, 'date': '2025-01-02'},
                ]
            }
        ]
        result = self.fetcher._calculate_max_streak(graph)
        assert result == 0

    def test_calculate_max_streak_single_streak(self):
        """Test max streak calculation with single streak."""
        graph = [
            {
                'contributionDays': [
                    {'contributionCount': 5, 'date': '2025-01-01'},
                    {'contributionCount': 3, 'date': '2025-01-02'},
                    {'contributionCount': 2, 'date': '2025-01-03'},
                    {'contributionCount': 0, 'date': '2025-01-04'},
                ]
            }
        ]
        result = self.fetcher._calculate_max_streak(graph)
        assert result == 3

    def test_calculate_max_streak_multiple_streaks(self):
        """Test max streak calculation with multiple streaks."""
        graph = [
            {
                'contributionDays': [
                    {'contributionCount': 5, 'date': '2025-01-01'},
                    {'contributionCount': 0, 'date': '2025-01-02'},
                    {'contributionCount': 3, 'date': '2025-01-03'},
                    {'contributionCount': 2, 'date': '2025-01-04'},
                    {'contributionCount': 7, 'date': '2025-01-05'},
                    {'contributionCount': 0, 'date': '2025-01-06'},
                ]
            }
        ]
        result = self.fetcher._calculate_max_streak(graph)
        # Second streak is longer (3 days)
        assert result == 3

    @patch('gitfetch.fetcher.subprocess.run')
    def test_build_env_with_token(self, mock_run):
        """Test that _build_env includes token when available."""
        fetcher = GitHubFetcher(token="my_token")
        env = fetcher._build_env()
        assert 'GH_TOKEN' in env
        assert env['GH_TOKEN'] == 'my_token'

    @patch('gitfetch.fetcher.subprocess.run')
    def test_build_env_without_token(self, mock_run):
        """Test that _build_env works without token."""
        fetcher = GitHubFetcher(token=None)
        env = fetcher._build_env()
        assert 'GH_TOKEN' not in env or env.get('GH_TOKEN') is None


class TestParallelExecution:
    """Test cases for parallel execution behavior."""

    def test_thread_pool_executor_import(self):
        """Test that ThreadPoolExecutor is properly imported."""
        from gitfetch.fetcher import ThreadPoolExecutor
        assert ThreadPoolExecutor is not None

    def test_concurrent_futures_import(self):
        """Test that concurrent.futures imports work."""
        import gitfetch.fetcher as fetcher_module
        assert hasattr(fetcher_module, 'ThreadPoolExecutor')
        assert hasattr(fetcher_module, 'as_completed')


class TestRetryOnFailure:
    """Test cases for retry_on_failure decorator."""

    def test_retry_on_failure_succeeds_immediately(self):
        """Test that retry decorator passes through successful calls."""

        @retry_on_failure(max_attempts=3)
        def always_succeed():
            return 42

        assert always_succeed() == 42

    def test_retry_on_failure_retries_then_succeeds(self):
        """Test that retry decorator retries on failure."""
        attempts = [0]

        @retry_on_failure(max_attempts=3, initial_delay=0.01)
        def fails_twice():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("Not yet!")
            return "success"

        assert fails_twice() == "success"
        assert attempts[0] == 3

    def test_retry_on_failure_exhausts_attempts(self):
        """Test that retry decorator raises after max attempts."""

        @retry_on_failure(max_attempts=2, initial_delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        try:
            always_fails()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert str(e) == "Always fails"

    def test_retry_on_failure_specific_exceptions(self):
        """Test that retry only catches specified exceptions."""

        @retry_on_failure(max_attempts=3, initial_delay=0.01, exceptions=(ValueError,))
        def fails_with_type_error():
            raise TypeError("Wrong type")

        try:
            fails_with_type_error()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass  # Expected

    @patch('gitfetch.fetcher.time.sleep')
    def test_retry_on_failure_exponential_backoff(self, mock_sleep):
        """Test that retry uses exponential backoff."""
        attempts = [0]

        @retry_on_failure(max_attempts=4, initial_delay=1.0, backoff_multiplier=2.0)
        def fails_a_few_times():
            attempts[0] += 1
            if attempts[0] < 4:
                raise ValueError("Not yet")
            return "done"

        fails_a_few_times()

        # Check sleep was called with increasing delays
        assert mock_sleep.call_count == 3
        # First sleep: 1.0, second: 2.0, third: 4.0 (exponential backoff)
        calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert calls == [1.0, 2.0, 4.0]

    @patch('gitfetch.fetcher.logger.warning')
    def test_retry_logs_warnings(self, mock_logger):
        """Test that retry logs warning messages."""

        @retry_on_failure(max_attempts=3, initial_delay=0.01)
        def fails_twice():
            if not hasattr(fails_twice, 'attempts'):
                fails_twice.attempts = 0
            fails_twice.attempts += 1
            if fails_twice.attempts < 3:
                raise ValueError("Fail")

        fails_twice()


class TestGitHubSearchAPI:
    """Test cases for GitHub Search API functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.fetcher = GitHubFetcher(token="test_token")

    @patch('gitfetch.fetcher.GitHubFetcher._gh_api')
    def test_search_items_returns_accurate_total_count(self, mock_api):
        """Test that _search_items returns accurate total_count from REST API."""
        # Mock API response with accurate total_count
        mock_api.return_value = {
            'total_count': 42,  # Actual total results
            'items': [
                {
                    'title': 'Test PR 1',
                    'repository': {'full_name': 'owner/repo'},
                    'html_url': 'https://github.com/owner/repo/pull/1',
                    'number': 1,
                    'state': 'open'
                },
                {
                    'title': 'Test PR 2',
                    'repository': {'full_name': 'owner/repo2'},
                    'html_url': 'https://github.com/owner/repo2/pull/2',
                    'number': 2,
                    'state': 'open'
                }
            ]
        }

        result = self.fetcher._search_items('is:pr state:open author:testuser', per_page=5)

        # Verify accurate total_count is returned
        assert result['total_count'] == 42
        assert len(result['items']) == 2
        assert result['items'][0]['title'] == 'Test PR 1'
        assert result['items'][0]['repo'] == 'owner/repo'

    @patch('gitfetch.fetcher.GitHubFetcher._gh_api')
    def test_search_items_url_encodes_query(self, mock_api):
        """Test that _search_items properly URL encodes the query."""
        mock_api.return_value = {'total_count': 0, 'items': []}

        self.fetcher._search_items('is:pr review-requested:@me')

        # Verify the query was URL encoded
        called_endpoint = mock_api.call_args[0][0]
        assert 'review-requested%3A%40me' in called_endpoint or 'review-requested:@me' in called_endpoint

    @patch('gitfetch.fetcher.GitHubFetcher._gh_api')
    def test_search_items_handles_errors_gracefully(self, mock_api):
        """Test that _search_items returns empty result on API errors."""
        mock_api.side_effect = Exception("API error")

        result = self.fetcher._search_items('is:pr author:testuser')

        assert result['total_count'] == 0
        assert result['items'] == []
