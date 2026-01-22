"""
Tests for search_query module
"""

import pytest
from gitfetch.search_query import (
    SearchQueryBuilder,
    build_pr_awaiting_review,
    build_pr_open,
    build_pr_mentions,
    build_pr_draft,
    build_pr_merged,
    build_pr_closed_recently,
    build_issue_assigned,
    build_issue_created,
    build_issue_mentions,
    build_issue_commented,
)


class TestSearchQueryBuilder:
    """Test SearchQueryBuilder class."""

    def test_empty_builder(self):
        """Test empty builder returns empty string."""
        builder = SearchQueryBuilder()
        assert builder.build() == ""

    def test_is_pr(self):
        """Test is:pr qualifier."""
        query = SearchQueryBuilder().is_pr().build()
        assert query == "is:pr"

    def test_is_issue(self):
        """Test is:issue qualifier."""
        query = SearchQueryBuilder().is_issue().build()
        assert query == "is:issue"

    def test_state_open(self):
        """Test state:open qualifier."""
        query = SearchQueryBuilder().state_open().build()
        assert query == "state:open"

    def test_state_closed(self):
        """Test state:closed qualifier."""
        query = SearchQueryBuilder().state_closed().build()
        assert query == "state:closed"

    def test_is_draft(self):
        """Test is:draft qualifier."""
        query = SearchQueryBuilder().is_draft().build()
        assert query == "is:draft"

    def test_is_merged(self):
        """Test is:merged qualifier."""
        query = SearchQueryBuilder().is_merged().build()
        assert query == "is:merged"

    def test_author(self):
        """Test author qualifier."""
        query = SearchQueryBuilder().author("username").build()
        assert query == "author:username"

    def test_assignee(self):
        """Test assignee qualifier."""
        query = SearchQueryBuilder().assignee("username").build()
        assert query == "assignee:username"

    def test_commenter(self):
        """Test commenter qualifier."""
        query = SearchQueryBuilder().commenter("username").build()
        assert query == "commenter:username"

    def test_mentions(self):
        """Test mentions qualifier."""
        query = SearchQueryBuilder().mentions("username").build()
        assert query == "mentions:username"

    def test_review_requested(self):
        """Test review-requested qualifier."""
        query = SearchQueryBuilder().review_requested("username").build()
        assert query == "review-requested:username"

    def test_closed_after(self):
        """Test closed:>= qualifier."""
        query = SearchQueryBuilder().closed_after("2025-01-01").build()
        assert query == "closed:>=2025-01-01"

    def test_closed_before(self):
        """Test closed:< qualifier."""
        query = SearchQueryBuilder().closed_before("2025-01-01").build()
        assert query == "closed:<2025-01-01"

    def test_created_after(self):
        """Test created:> qualifier."""
        query = SearchQueryBuilder().created_after("2025-01-01").build()
        assert query == "created:>2025-01-01"

    def test_created_before(self):
        """Test created:< qualifier."""
        query = SearchQueryBuilder().created_before("2025-01-01").build()
        assert query == "created:<2025-01-01"

    def test_updated_after(self):
        """Test updated:> qualifier."""
        query = SearchQueryBuilder().updated_after("2025-01-01").build()
        assert query == "updated:>2025-01-01"

    def test_updated_before(self):
        """Test updated:< qualifier."""
        query = SearchQueryBuilder().updated_before("2025-01-01").build()
        assert query == "updated:<2025-01-01"

    def test_in_repo(self):
        """Test repo qualifier."""
        query = SearchQueryBuilder().in_repo("owner/repo").build()
        assert query == "repo:owner/repo"

    def test_in_repos(self):
        """Test multiple repo qualifiers."""
        query = SearchQueryBuilder().in_repos("owner/repo1", "owner/repo2").build()
        assert query == "repo:owner/repo1 repo:owner/repo2"

    def test_label(self):
        """Test label qualifier."""
        query = SearchQueryBuilder().label("bug").build()
        assert query == "label:bug"

    def test_labels(self):
        """Test multiple label qualifiers."""
        query = SearchQueryBuilder().labels("bug", "enhancement").build()
        assert query == "label:bug label:enhancement"

    def test_no_label(self):
        """Test no:label qualifier."""
        query = SearchQueryBuilder().no_label().build()
        assert query == "no:label"

    def test_is_locked(self):
        """Test is:locked qualifier."""
        query = SearchQueryBuilder().is_locked().build()
        assert query == "is:locked"

    def test_is_unlocked(self):
        """Test is:unlocked qualifier."""
        query = SearchQueryBuilder().is_unlocked().build()
        assert query == "is:unlocked"

    def test_comments(self):
        """Test comments qualifier."""
        query = SearchQueryBuilder().comments(42).build()
        assert query == "comments:42"

    def test_comments_greater_than(self):
        """Test comments:> qualifier."""
        query = SearchQueryBuilder().comments_greater_than(42).build()
        assert query == "comments:>42"

    def test_comments_less_than(self):
        """Test comments:< qualifier."""
        query = SearchQueryBuilder().comments_less_than(42).build()
        assert query == "comments:<42"

    def test_add_custom(self):
        """Test custom qualifier."""
        query = SearchQueryBuilder().add_custom("status:success").build()
        assert query == "status:success"

    def test_chaining_multiple_qualifiers(self):
        """Test method chaining with multiple qualifiers."""
        query = SearchQueryBuilder().is_pr().state_open().author("username").build()
        assert query == "is:pr state:open author:username"

    def test_complex_query(self):
        """Test complex query with many qualifiers."""
        query = (
            SearchQueryBuilder()
            .is_pr()
            .state_open()
            .author("username")
            .in_repo("owner/repo")
            .label("bug")
            .created_after("2025-01-01")
            .build()
        )
        assert (
            query
            == "is:pr state:open author:username repo:owner/repo label:bug created:>2025-01-01"
        )

    def test_reset(self):
        """Test reset clears all qualifiers."""
        builder = SearchQueryBuilder()
        builder.is_pr().state_open()
        assert builder.build() == "is:pr state:open"
        builder.reset()
        assert builder.build() == ""

    def test_str_method(self):
        """Test __str__ method."""
        builder = SearchQueryBuilder()
        builder.is_pr()
        assert str(builder) == "is:pr"

    def test_repr_method(self):
        """Test __repr__ method."""
        builder = SearchQueryBuilder()
        builder.is_pr()
        assert repr(builder) == "SearchQueryBuilder('is:pr')"

    def test_fluent_interface(self):
        """Test fluent interface pattern."""
        builder = SearchQueryBuilder().is_pr().state_open().author("testuser")
        # Should be able to continue chaining
        query = builder.mentions("anotheruser").build()
        assert query == "is:pr state:open author:testuser mentions:anotheruser"


class TestPrebuiltQueries:
    """Test prebuilt query functions."""

    def test_build_pr_awaiting_review(self):
        """Test PRs awaiting review query."""
        query = build_pr_awaiting_review("username")
        assert query == "is:pr state:open review-requested:username"

    def test_build_pr_open(self):
        """Test open PRs query."""
        query = build_pr_open("username")
        assert query == "is:pr state:open author:username"

    def test_build_pr_mentions(self):
        """Test PR mentions query."""
        query = build_pr_mentions("username")
        assert query == "is:pr state:open mentions:username"

    def test_build_pr_draft(self):
        """Test draft PRs query."""
        query = build_pr_draft("username")
        assert query == "is:pr is:draft author:username"

    def test_build_pr_merged(self):
        """Test merged PRs query."""
        query = build_pr_merged("username")
        assert query == "is:pr is:merged author:username"

    def test_build_pr_closed_recently(self):
        """Test PRs closed recently query."""
        query = build_pr_closed_recently("username", "2025-01-01")
        assert query == "is:pr state:closed author:username closed:>=2025-01-01"

    def test_build_issue_assigned(self):
        """Test assigned issues query."""
        query = build_issue_assigned("username")
        assert query == "is:issue state:open assignee:username"

    def test_build_issue_created(self):
        """Test created issues query."""
        query = build_issue_created("username")
        assert query == "is:issue state:open author:username"

    def test_build_issue_mentions(self):
        """Test issue mentions query."""
        query = build_issue_mentions("username")
        assert query == "is:issue state:open mentions:username"

    def test_build_issue_commented(self):
        """Test commented issues query."""
        query = build_issue_commented("username")
        assert query == "is:issue state:open commenter:username"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_username(self):
        """Test with empty username."""
        query = build_pr_open("")
        assert query == "is:pr state:open author:"

    def test_special_characters_in_username(self):
        """Test with special characters in username."""
        query = SearchQueryBuilder().author("user-name").build()
        assert query == "author:user-name"

    def test_date_format(self):
        """Test date format handling."""
        query = SearchQueryBuilder().created_after("2025-12-31").build()
        assert query == "created:>2025-12-31"

    def test_reuse_builder(self):
        """Test reusing builder after build."""
        builder = SearchQueryBuilder()
        query1 = builder.is_pr().build()
        assert query1 == "is:pr"
        builder.reset()
        query2 = builder.is_issue().build()
        assert query2 == "is:issue"

    def test_no_qualifiers(self):
        """Test building with no qualifiers."""
        builder = SearchQueryBuilder()
        assert builder.build() == ""
        assert str(builder) == ""
