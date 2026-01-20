# Gitfetch CLI Improvement Roadmap

> **Status:** Draft - Ready for review and iteration
> **Last Updated:** 2025-01-20
> **Location:** `/Users/matar/fafo/gitfetch_root/gitfetch/src/gitfetch/`

---

## Working Instructions (Ralph Loop)

**After EACH iteration, you MUST:**

1. **Update `log.md`** - Append what you completed in this iteration:
   ```markdown
   ### Iteration N
   - [x] Completed task X
   - [x] Fixed bug Y
   ```

2. **Update `task.md`** - Remove completed items from this file:
   - Remove entire sections that are fully done
   - Mark items as `[DONE]` if partially complete
   - This keeps the prompt focused on remaining work

3. **Check for completion** - When all Priority 1 items are done, output:
   ```
   <promise>PRIORITY1_COMPLETE</promise>
   ```

4. **Files to track:**
   - `task.md` - This file (shrinks as work completes)
   - `log.md` - Achievement log (grows as work completes)

---

## Project Overview

Gitfetch is a neofetch-style CLI tool for GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut statistics.

**Core Files:**
```
gitfetch/src/gitfetch/
├── __init__.py       # v0.6.x, package init, version detection
├── cli.py            # 668 lines - CLI entry point, argument parsing
├── fetcher.py        # 957 lines - Git provider data fetchers (4 providers)
├── cache.py          # 377 lines - SQLite-based caching
├── config.py         # 422 lines - Configuration management
├── display.py        # ~1700 lines - Terminal display formatting
├── providers.py      # Provider definitions & dataclasses
└── text_patterns.py  # ASCII art patterns
```

**Dependencies:**
- `requests>=2.0.0` - HTTP requests
- `readchar>=4.0.0` - Terminal input
- `webcolors>=24.11.1` - Color conversion
- External: `gh` (GitHub CLI), `glab` (GitLab CLI)

---

## [DONE] Priority 1: Critical Bugs & Robustness

All Priority 1 items completed in Iteration 1. See `log.md` for details.

---

## Priority 2: Performance & Responsiveness

### 2.1 No Parallel API Fetching
**Severity:** High (UX impact)
**File:** `fetcher.py`

**Current Behavior:**
- `_fetch_repos()` - Sequential pagination
- PR search - Sequential
- Issue search - Sequential
- Contribution graph - Separate call

**Proposed Solution:**
```python
from concurrent.futures import ThreadPoolExecutor

def fetch_user_stats(self, username, user_data=None):
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_repos = executor.submit(self._fetch_repos, username)
        future_graph = executor.submit(self._fetch_contribution_graph, username)
        future_prs = executor.submit(self._fetch_pull_requests, username)
        future_issues = executor.submit(self._fetch_issues, username)

        repos = future_repos.result()
        contrib_graph = future_graph.result()
        # ...
```

**Expected Speedup:** ~3-4x for users with many repos/PRs

### 2.2 No Loading Indicators
**Severity:** Medium (UX impact)
**File:** `cli.py`

**Current Behavior:**
- Application appears frozen during API calls
- No feedback for 5-30 second operations

**Proposed Solution:**
- Add spinner using `rich.progress` or similar
- Show "Fetching data from GitHub..." with spinner
- Display "Refreshing cache in background..." when applicable

### 2.3 No Retry Mechanism
**Severity:** Medium
**File:** `fetcher.py`

**Current Behavior:**
- Network errors = immediate failure
- Timeout = immediate failure

**Proposed Solution:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def _api_request(self, endpoint):
    # existing code
```

### 2.4 No Rate Limit Awareness
**Severity:** Low-Medium
**Files:** `fetcher.py`, `cli.py`

**Current Behavior:**
- No rate limit detection
- Can hit API limits unexpectedly

**Proposed Solution:**
- Parse `X-RateLimit-*` headers from GitHub API
- Display warning when >80% of quota used
- Implement backoff when rate limited

---

## Priority 3: Calculations & Data Accuracy

### 3.1 Duplicate Streak Calculation
**Severity:** Medium
**Files:** `fetcher.py`, `display.py`

**Issue:** Streak is calculated in TWO places with potentially different results:
- `fetcher.py:274-292` - Calculates `current_streak` in fetcher
- `display.py:1103-1137` - Calculates `current_streak` and `max_streak` in display

**Problems:**
1. Fetcher calculates only `current_streak`, not `max_streak`
2. Display recalculates both, ignoring cached `current_streak` from fetcher
3. Inconsistent results if data changes between fetch and display
4. Wasted CPU cycles (double calculation)

**Fix:**
- Move all streak calculation to one place (fetcher)
- Cache both `current_streak` and `max_streak`
- Display should use cached values, not recalculate

### 3.2 Duplicate Total Contributions Calculation
**Severity:** Low
**Files:** `fetcher.py`, `display.py`

**Issue:** `total_contributions` is calculated in display.py multiple times:
- `display.py:669-673` - In `_format_user_info_compact`
- `display.py:699-703` - In `_format_user_info`
- `display.py:1262-1268` - In `_calculate_total_contributions`

**Problems:**
1. Not cached in `fetcher.py` - always recalculated in display
2. Called multiple times per display call
3. Expensive iteration through all weeks/days

**Fix:**
- Calculate `total_contributions` once in `fetcher.py:fetch_user_stats()`
- Cache it in stats dict
- Display should use cached value

### 3.3 GitHub Search Limitations
**Severity:** Medium
**File:** `fetcher.py:432-514`

**Current Behavior:**
```python
def _search_items(self, query: str, per_page: int = 5) -> Dict[str, Any]:
    # Uses `gh search` command with --limit 5
    # Returns only 5 items
    return {
        'total_count': len(items),  # BUG: This is items returned, NOT actual total!
        'items': items
    }
```

**Issues:**
1. `total_count` is `len(items)` (max 5), not the actual search result count
2. No pagination - misses PRs/issues beyond first 5
3. Hardcoded limit of 5 cannot be changed
4. `gh search` CLI may return different results than GraphQL API

**Impact:**
- User sees "5" for awaiting review PRs when they actually have 23
- No way to see all PRs/issues
- Misleading counts

**Fix:**
- Use GraphQL API for accurate counts (supports `totalCount`)
- Add pagination support or increase limit
- Make `per_page` configurable
- Show accurate counts like "23 awaiting review (showing 5)"

### 3.4 PR/Issue Categories Incomplete
**Severity:** Low
**File:** `fetcher.py`

**Missing Categories:**
- No "Draft PRs" category
- No "Closed recently" category
- No "Your PRs merged" category
- No "Issues you commented on"
- No "Reviewed PRs" category

**Current Categories:**
- Awaiting Review
- Your Open PRs
- Mentions
- Assigned Issues
- Created Issues
- Mentions (issues)

### 3.5 Contribution Graph Color Mapping Inconsistent
**Severity:** Low
**Files:** `display.py:1324-1375`

**Issue:** Two separate functions for color mapping with inconsistent logic:
- `_get_contribution_block()` - Uses background colors (spaces)
- `_get_contribution_block_spaced()` - Uses foreground colors (custom box)

**Color thresholds differ from GitHub:**
```python
# Gitfetch thresholds:
if count == 0: level = '0'
elif count < 3: level = '1'
elif count < 7: level = '2'
elif count < 13: level = '3'
else: level = '4'

# GitHub actual thresholds:
# 0, 1-2, 3-5, 6-9, 10+
```

**GitHub uses:** 0, 1-2, 3-5, 6-9, 10+
**Gitfetch uses:** 0, 1-2, 3-6, 7-12, 13+

### 3.6 Language Percentage Calculation Issue
**Severity:** Low
**File:** `fetcher.py:387-430`

**Issue:** Language calculation is based on repository count, not actual code size.

```python
# Current: Counts repos that USE each language
for repo in repos:
    language = repo.get('language')
    if language:
        language_occurrences[normalized][language] += 1
```

**Problem:** A repo with 1000 lines of Rust counts same as repo with 10 lines of JavaScript.

**GitHub's approach:** Uses actual bytes of code per language.

### 3.7 No Longest Streak Calculation
**Severity:** Low
**File:** `display.py:1103-1137`

**Issue:** `max_streak` calculation is incorrect - it finds the longest streak ANYWHERE in history, not necessarily the longest historical streak.

**Current logic:**
```python
for contrib in all_contributions:
    if contrib > 0:
        temp_streak += 1
        if temp_streak > max_streak:
            max_streak = temp_streak
    else:
        temp_streak = 0
```

**This finds:** Longest consecutive sequence anywhere (correct)
**But:** May not align with user's expectation of "best streak"

---

## Priority 4: Code Quality & Testing

### 4.1 Minimal Test Coverage
**Severity:** High
**Current State:** Only `tests/test_cache.py` with 4 tests

**Coverage Analysis:**
| Module | Lines | Coverage |
|--------|-------|----------|
| `cache.py` | 377 | ~60% (only tests exist) |
| `cli.py` | 668 | 0% |
| `fetcher.py` | 957 | 0% |
| `config.py` | 422 | 0% |
| `display.py` | ~1700 | 0% |

**Required Tests:**
1. **Fetcher tests** (mock subprocess/API calls)
   - Test each provider (GitHub, GitLab, Gitea, Sourcehut)
   - Test error scenarios
   - Test timeout handling

2. **CLI tests**
   - Argument parsing
   - Provider selection
   - Cache clear/version commands

3. **Config tests**
   - Load/save config
   - Migration logic
   - Color handling

4. **Display tests**
   - Output formatting
   - Graph generation
   - Streak calculations

5. **Calculation tests**
   - Total contributions
   - Streak calculation (current and max)
   - Language percentages

**Target:** 80%+ code coverage

### 4.2 Type Hints Inconsistency
**Severity:** Low
**Issue:** Type hints present but incomplete

**Fix:**
```bash
# Run mypy strict mode
mypy src/gitfetch --strict
```

### 4.3 Long Functions
**Severity:** Low (maintainability)
**Files:** `cli.py`, `display.py`, `fetcher.py`

**Functions >100 lines:**
- `cli.py:main()` - ~270 lines
- `cli.py:_initialize_gitfetch()` - ~100 lines
- `display.py:display()` - very long
- `display.py:_get_graph_text()` - ~55 lines
- `display.py:_build_month_line_spaced()` - ~60 lines
- `fetcher.py:fetch_user_stats()` - ~80 lines
- `fetcher.py:_search_items()` - ~50 lines
- `fetcher.py:_parse_search_query()` - ~30 lines

---

## Priority 5: Refactoring Opportunities

### 5.1 Duplicate Calculation Logic
**Severity:** Medium
**Files:** `fetcher.py`, `display.py`

**Issue:** Calculations scattered across modules, duplicated efforts

**Create:** `gitfetch/calculations.py` - New module for all calculations

**Functions to extract:**
```python
# New module: calculations.py

def calculate_total_contributions(weeks_data: list) -> int:
    """Sum total contributions across all weeks."""
    # Move from display.py:1262-1268

def calculate_streaks(weeks_data: list) -> tuple[int, int]:
    """Calculate current and max streak.

    Returns:
        (current_streak, max_streak)
    """
    # Move from display.py:1103-1137
    # Merge with fetcher.py:274-292 logic

def calculate_language_stats(repos: list) -> dict[str, float]:
    """Calculate language usage from repositories.

    Uses repository primary language count.
    TODO: Use actual code bytes for accuracy.
    """
    # Move from fetcher.py:387-430

def get_contribution_color_level(count: int) -> int:
    """Map contribution count to color level (0-4).

    Uses GitHub thresholds: 0, 1-2, 3-5, 6-9, 10+
    """
    # Centralize color mapping logic
```

### 5.2 Search Query Parser
**Severity:** Low
**File:** `fetcher.py:483-514`

**Issue:** `_parse_search_query()` is complex and hard to test

**Refactor:**
- Extract to separate class `SearchQueryBuilder`
- Make testable with input/output
- Support more query operators

### 5.3 Display Layout Strategy Pattern
**Severity:** Low
**File:** `display.py`

**Issue:** `_display_full`, `_display_compact`, `_display_minimal` have duplicated code

**Refactor:**
```python
# Strategy pattern for layouts
class LayoutStrategy(ABC):
    @abstractmethod
    def render(self, username, user_data, stats, spaced): ...

class MinimalLayout(LayoutStrategy):
    def render(self, ...): ...

class CompactLayout(LayoutStrategy):
    def render(self, ...): ...

class FullLayout(LayoutStrategy):
    def render(self, ...): ...
```

### 5.4 Provider Factory Pattern
**Severity:** Low
**File:** `cli.py:538-554`

**Issue:** `_create_fetcher()` uses if/elif chain

**Current:**
```python
def _create_fetcher(provider, base_url, token):
    if provider == 'github':
        from .fetcher import GitHubFetcher
        return GitHubFetcher(token)
    elif provider == 'gitlab':
        # ...
```

**Refactor:**
```python
# Provider registry pattern
FETCHER_REGISTRY = {
    'github': GitHubFetcher,
    'gitlab': GitLabFetcher,
    'gitea': GiteaFetcher,
    'sourcehut': SourcehutFetcher,
}

def create_fetcher(provider, base_url, token):
    fetcher_class = FETCHER_REGISTRY.get(provider)
    if not fetcher_class:
        raise ValueError(f"Unknown provider: {provider}")
    return fetcher_class(base_url, token)
```

### 5.5 Configuration Validation
**Severity:** Medium
**File:** `config.py`

**Issue:** No validation on load/save

**Create:** `gitfetch/validators.py`

```python
def validate_url(url: str) -> bool:
    """Validate URL format."""
    from urllib.parse import urlparse
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def validate_github_token(token: str) -> bool:
    """GitHub personal access tokens are 40 hex characters."""
    return bool(re.match(r'^[a-f0-9]{40}$', token))

def validate_cache_expiry(minutes: int) -> bool:
    """Cache expiry must be between 1 and 5256000 (10 years)."""
    return 1 <= minutes <= 5256000
```

### 5.6 Error Hierarchy
**Severity:** Low

**Create:** `gitfetch/exceptions.py`

```python
class GitfetchError(Exception):
    """Base exception for gitfetch."""

class FetcherError(GitfetchError):
    """Error fetching data from provider."""

class CacheError(GitfetchError):
    """Error with cache operations."""

class ConfigError(GitfetchError):
    """Error with configuration."""

class RateLimitError(FetcherError):
    """API rate limit exceeded."""

class AuthenticationError(FetcherError):
    """Authentication failed."""
```

### 5.7 Constants Module
**Severity:** Low

**Create:** `gitfetch/constants.py`

```python
# Contribution color levels (GitHub thresholds)
CONTRIBUTION_THRESHOLDS = [0, 1, 3, 6, 10]

# Default cache expiry
DEFAULT_CACHE_MINUTES = 15

# Search limits
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 100

# Display settings
DEFAULT_TERMINAL_WIDTH = 80
MIN_TERMINAL_WIDTH = 40
```

---

## Priority 6: User Experience

### 6.1 Generic Error Messages
**Severity:** Medium
**Examples:**
- "Error: Failed" (no context)
- "Could not get authenticated user" (no solution)

**Proposed Improvements:**
```
"Error: GitHub CLI (gh) is not installed!
Install it with:
  macOS: brew install gh
  Linux: https://github.com/cli/cli#installation
Then run: gh auth login"
```

### 6.2 No Cancellation Support
**Severity:** Low
**File:** `cli.py`

**Current:** KeyboardInterrupt handled only at top level

**Proposed:**
- Graceful cleanup of subprocesses
- Close SQLite connections
- Save partial data if possible

---

## Priority 7: Security

### 7.1 Plaintext Token Storage
**Severity:** Low (documented limitation)
**File:** `config.py`

**Current:** Tokens stored in `~/.config/gitfetch/gitfetch.conf`

**Proposed:**
- Document security implications
- Support environment variables only mode
- Consider OS keychain integration (future)

### 7.2 Token Logging
**Severity:** Low
**Audit needed:** Check if tokens appear in error messages

**Fix:** Redact tokens in all error paths

---

## Priority 8: Platform-Specific Improvements

### 8.1 Sourcehut Support
**Severity:** Low
**File:** `fetcher.py:SourcehutFetcher`

**Current:** All stats return 0

**Proposed:**
- Implement proper GraphQL queries
- Fetch actual repo count if available

### 8.2 Windows Support
**Severity:** Low

**Current:** Not tested on Windows

**Proposed:**
- Test on Windows
- Fix path handling (use `pathlib` everywhere)
- Document Windows limitations

---

## Implementation Phases

### Phase 1: Foundation (Critical Bugs)
**Estimated Tasks:** 10-12
1. Add logging infrastructure
2. Fix silent failures in `cache.py`
3. Fix resource leaks (SQLite, file handles)
4. Fix exception handling in `_is_cache_expired`
5. Add tests for cache.py (expand existing)
6. Verify all fixes with tests

**Files to modify:**
- `gitfetch/src/gitfetch/cache.py`
- `gitfetch/src/gitfetch/cli.py`
- `gitfetch/src/gitfetch/fetcher.py`
- `gitfetch/tests/test_cache.py`

### Phase 2: Calculations & Data Accuracy
**Estimated Tasks:** 8-10
1. Create `calculations.py` module
2. Move streak calculation to one place
3. Fix `total_contributions` caching
4. Fix GitHub search total_count bug
5. Fix contribution color thresholds to match GitHub
6. Add calculation tests

**Files to create:**
- `gitfetch/src/gitfetch/calculations.py`
- `gitfetch/tests/test_calculations.py`

**Files to modify:**
- `gitfetch/src/gitfetch/fetcher.py`
- `gitfetch/src/gitfetch/display.py`

### Phase 3: Test Coverage
**Estimated Tasks:** 15-20
1. Add test infrastructure (fixtures, mocks)
2. Test all fetcher classes
3. Test CLI argument parsing
4. Test config management
5. Add CI coverage reporting

**Files to create:**
- `gitfetch/tests/test_fetcher.py`
- `gitfetch/tests/test_cli.py`
- `gitfetch/tests/test_config.py`
- `gitfetch/tests/conftest.py`

### Phase 4: Refactoring
**Estimated Tasks:** 10-15
1. Create `exceptions.py` module
2. Create `constants.py` module
3. Create `validators.py` module
4. Implement provider factory pattern
5. Refactor display layout strategy
6. Refactor search query parser

**Files to create:**
- `gitfetch/src/gitfetch/exceptions.py`
- `gitfetch/src/gitfetch/constants.py`
- `gitfetch/src/gitfetch/validators.py`

### Phase 5: Performance
**Estimated Tasks:** 8-12
1. Add parallel API fetching
2. Add loading indicators
3. Add retry mechanism
4. Add rate limit awareness

### Phase 6: UX Polish
**Estimated Tasks:** 5-8
1. Improve error messages
2. Better cancellation handling

### Phase 7: Security
**Estimated Tasks:** 3-5
1. Audit token handling
2. Add token redaction
3. Document security model

### Phase 8: Platform Enhancements
**Estimated Tasks:** 3-5
1. Improve Sourcehut support
2. Add Windows testing
3. Document platform differences

---

## Quick Reference: File Locations

| File | Path | Purpose |
|------|------|---------|
| CLI | `/Users/matar/fafo/gitfetch_root/gitfetch/src/gitfetch/cli.py` | Entry point |
| Fetcher | `/Users/matar/fafo/gitfetch_root/gitfetch/src/gitfetch/fetcher.py` | API calls |
| Cache | `/Users/matar/fafo/gitfetch_root/gitfetch/src/gitfetch/cache.py` | SQLite cache |
| Config | `/Users/matar/fafo/gitfetch_root/gitfetch/src/gitfetch/config.py` | Settings |
| Display | `/Users/matar/fafo/gitfetch_root/gitfetch/src/gitfetch/display.py` | Output |
| Tests | `/Users/matar/fafo/gitfetch_root/gitfetch/tests/` | Test suite |
| Config file | `~/.config/gitfetch/gitfetch.conf` | User config |
| Cache DB | `~/.local/share/gitfetch/cache.db` | Local cache |

---

## Notes

- This is a **living document** - update as we iterate
- Each task should have its own branch/PR
- Maintain **backward compatibility** where possible
- **All changes must include tests**
- Follow existing code style (Black formatter)
