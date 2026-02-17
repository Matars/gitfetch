"""
GitHub Search Query Builder

This module provides a fluent interface for building GitHub search queries
for issues and pull requests. Makes query construction testable and maintainable.

Example:
    >>> builder = SearchQueryBuilder()
    >>> query = builder.is_pr().state_open().author("username").build()
    >>> print(query)
    'is:pr state:open author:username'
"""

from typing import List, Optional


class SearchQueryBuilder:
    """
    Builder for constructing GitHub search queries.

    Supports common GitHub search qualifiers for issues and pull requests:
    - Type: is:issue, is:pr
    - State: state:open, state:closed
    - Status: is:draft, is:merged
    - Actors: author:, assignee:, commenter:, mentions:, review-requested:
    - Dates: closed:>=, created:>, updated:<, etc.

    See: https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
    """

    def __init__(self) -> None:
        """Initialize an empty query builder."""
        self._qualifiers: List[str] = []

    def is_pr(self) -> "SearchQueryBuilder":
        """Filter to pull requests only (is:pr)."""
        self._qualifiers.append("is:pr")
        return self

    def is_issue(self) -> "SearchQueryBuilder":
        """Filter to issues only (is:issue)."""
        self._qualifiers.append("is:issue")
        return self

    def state_open(self) -> "SearchQueryBuilder":
        """Filter to open items (state:open)."""
        self._qualifiers.append("state:open")
        return self

    def state_closed(self) -> "SearchQueryBuilder":
        """Filter to closed items (state:closed)."""
        self._qualifiers.append("state:closed")
        return self

    def is_draft(self) -> "SearchQueryBuilder":
        """Filter to draft PRs (is:draft)."""
        self._qualifiers.append("is:draft")
        return self

    def is_merged(self) -> "SearchQueryBuilder":
        """Filter to merged PRs (is:merged)."""
        self._qualifiers.append("is:merged")
        return self

    def author(self, username: str) -> "SearchQueryBuilder":
        """Filter by author (author:username)."""
        self._qualifiers.append(f"author:{username}")
        return self

    def assignee(self, username: str) -> "SearchQueryBuilder":
        """Filter by assignee (assignee:username)."""
        self._qualifiers.append(f"assignee:{username}")
        return self

    def commenter(self, username: str) -> "SearchQueryBuilder":
        """Filter by commenter (commenter:username)."""
        self._qualifiers.append(f"commenter:{username}")
        return self

    def mentions(self, username: str) -> "SearchQueryBuilder":
        """Filter by mentions (mentions:username)."""
        self._qualifiers.append(f"mentions:{username}")
        return self

    def review_requested(self, username: str) -> "SearchQueryBuilder":
        """Filter by review requested (review-requested:username)."""
        self._qualifiers.append(f"review-requested:{username}")
        return self

    def closed_after(self, date: str) -> "SearchQueryBuilder":
        """Filter items closed after date (closed:>=YYYY-MM-DD)."""
        self._qualifiers.append(f"closed:>={date}")
        return self

    def closed_before(self, date: str) -> "SearchQueryBuilder":
        """Filter items closed before date (closed:<YYYY-MM-DD)."""
        self._qualifiers.append(f"closed:<{date}")
        return self

    def created_after(self, date: str) -> "SearchQueryBuilder":
        """Filter items created after date (created:>YYYY-MM-DD)."""
        self._qualifiers.append(f"created:>{date}")
        return self

    def created_before(self, date: str) -> "SearchQueryBuilder":
        """Filter items created before date (created:<YYYY-MM-DD)."""
        self._qualifiers.append(f"created:<{date}")
        return self

    def updated_after(self, date: str) -> "SearchQueryBuilder":
        """Filter items updated after date (updated:>YYYY-MM-DD)."""
        self._qualifiers.append(f"updated:>{date}")
        return self

    def updated_before(self, date: str) -> "SearchQueryBuilder":
        """Filter items updated before date (updated:<YYYY-MM-DD)."""
        self._qualifiers.append(f"updated:<{date}")
        return self

    def in_repo(self, repo: str) -> "SearchQueryBuilder":
        """Filter by repository (repo:owner/name)."""
        self._qualifiers.append(f"repo:{repo}")
        return self

    def in_repos(self, *repos: str) -> "SearchQueryBuilder":
        """Filter by multiple repositories (repo:owner/name repo:owner/name2)."""
        for repo in repos:
            self._qualifiers.append(f"repo:{repo}")
        return self

    def label(self, label_name: str) -> "SearchQueryBuilder":
        """Filter by label (label:bug)."""
        self._qualifiers.append(f"label:{label_name}")
        return self

    def labels(self, *label_names: str) -> "SearchQueryBuilder":
        """Filter by multiple labels (label:bug label:enhancement)."""
        for label in label_names:
            self._qualifiers.append(f"label:{label}")
        return self

    def no_label(self) -> "SearchQueryBuilder":
        """Filter items with no labels (no:label)."""
        self._qualifiers.append("no:label")
        return self

    def is_locked(self) -> "SearchQueryBuilder":
        """Filter to locked conversations (is:locked)."""
        self._qualifiers.append("is:locked")
        return self

    def is_unlocked(self) -> "SearchQueryBuilder":
        """Filter to unlocked conversations (is:unlocked)."""
        self._qualifiers.append("is:unlocked")
        return self

    def comments(self, count: int) -> "SearchQueryBuilder":
        """Filter by number of comments (comments:42)."""
        self._qualifiers.append(f"comments:{count}")
        return self

    def comments_greater_than(self, count: int) -> "SearchQueryBuilder":
        """Filter by comments greater than (comments:>42)."""
        self._qualifiers.append(f"comments:>{count}")
        return self

    def comments_less_than(self, count: int) -> "SearchQueryBuilder":
        """Filter by comments less than (comments:<42)."""
        self._qualifiers.append(f"comments:<{count}")
        return self

    def add_custom(self, qualifier: str) -> "SearchQueryBuilder":
        """
        Add a custom qualifier not supported by the builder.

        Args:
            qualifier: Custom qualifier string (e.g., "status:success")

        Returns:
            Self for chaining
        """
        self._qualifiers.append(qualifier)
        return self

    def build(self) -> str:
        """
        Build the final query string.

        Returns:
            Space-separated query string ready for GitHub Search API
        """
        return " ".join(self._qualifiers)

    def reset(self) -> "SearchQueryBuilder":
        """Clear all qualifiers and start fresh."""
        self._qualifiers.clear()
        return self

    def __str__(self) -> str:
        """Return the query string when used as a string."""
        return self.build()

    def __repr__(self) -> str:
        """Return representation of the builder."""
        return f"SearchQueryBuilder('{self.build()}')"


def build_pr_awaiting_review(username: str) -> str:
    """
    Build query for PRs awaiting review by user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return (
        SearchQueryBuilder()
        .is_pr()
        .state_open()
        .review_requested(username)
        .build()
    )


def build_pr_open(username: str) -> str:
    """
    Build query for open PRs by user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_pr().state_open().author(username).build()


def build_pr_mentions(username: str) -> str:
    """
    Build query for open PRs mentioning user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_pr().state_open().mentions(username).build()


def build_pr_draft(username: str) -> str:
    """
    Build query for draft PRs by user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_pr().is_draft().author(username).build()


def build_pr_merged(username: str) -> str:
    """
    Build query for merged PRs by user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_pr().is_merged().author(username).build()


def build_pr_closed_recently(username: str, date: str) -> str:
    """
    Build query for PRs closed after given date by user.

    Args:
        username: GitHub username
        date: Date in YYYY-MM-DD format

    Returns:
        Search query string
    """
    return (
        SearchQueryBuilder()
        .is_pr()
        .state_closed()
        .author(username)
        .closed_after(date)
        .build()
    )


def build_issue_assigned(username: str) -> str:
    """
    Build query for open issues assigned to user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_issue().state_open().assignee(username).build()


def build_issue_created(username: str) -> str:
    """
    Build query for open issues created by user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_issue().state_open().author(username).build()


def build_issue_mentions(username: str) -> str:
    """
    Build query for open issues mentioning user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_issue().state_open().mentions(username).build()


def build_issue_commented(username: str) -> str:
    """
    Build query for open issues commented by user.

    Args:
        username: GitHub username

    Returns:
        Search query string
    """
    return SearchQueryBuilder().is_issue().state_open().commenter(username).build()
