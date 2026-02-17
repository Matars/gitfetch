# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gitfetch is a neofetch-style CLI tool that displays statistics from GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut in a terminal interface. It features ASCII art contribution graphs, streak tracking, and extensive customization options.

The project has two components:
- **Python CLI** (`src/gitfetch/`): Main application with caching, multi-provider support, and rich terminal display
- **Rust TUI** (`rust/gitfetch-tui/`): Experimental ratatui-based interface for daily git workflow (stage/commit/push)

## Common Commands

```bash
# Install for development
make dev

# Run tests
make test
python3 -m pytest tests/ -v

# Run single test file
python3 -m pytest tests/test_cache.py -v

# Run single test
python3 -m pytest tests/test_cli.py::test_function_name -v

# Clean build artifacts
make clean

# Run the CLI locally
gitfetch [username]
gitfetch --tui  # Launch experimental Rust TUI

# Run Rust TUI from source
cargo run --manifest-path rust/gitfetch-tui/Cargo.toml
```

## Architecture

### Python CLI Structure

```
src/gitfetch/
├── cli.py          # Entry point, argument parsing, provider initialization
├── fetcher.py      # Provider fetchers (GitHubFetcher, GitLabFetcher, GiteaFetcher, SourcehutFetcher)
├── display.py      # Terminal rendering, contribution graph visualization, layout management
├── cache.py        # SQLite-based caching with stale-while-revalidate pattern
├── config.py       # ConfigManager: ~/.config/gitfetch/gitfetch.conf management
├── providers.py    # ProviderConfig dataclass, env var mappings, default URLs
├── calculations.py # Streak/contribution calculations
├── constants.py    # Magic values (timeouts, thresholds)
├── text_patterns.py # ASCII patterns for --text and --shape modes
```

### Key Design Patterns

**Provider Abstraction**: `BaseFetcher` ABC defines the interface; each provider (GitHub, GitLab, Gitea, Sourcehut) implements `fetch_user_data()`, `fetch_user_stats()`, and `get_authenticated_user()`. GitHub/GitLab use their respective CLIs (`gh`, `glab`) for authentication.

**Caching**: SQLite-based with background refresh. If cache is stale but exists, displays immediately and spawns a background subprocess to refresh.

**Display Layout**: Adaptive layout system that chooses between "full", "compact", and "minimal" based on terminal dimensions. Contribution graph renders week columns with configurable intensity colors.

### Rust TUI

Single-file application (`rust/gitfetch-tui/src/main.rs`) using ratatui/crossterm. Features:
- Real-time file change monitoring
- Git staging/unstaging
- Commit modal with message input
- Push operations
- Worktree management with embedded terminal via portable-pty

## Configuration

Config stored at `~/.config/gitfetch/gitfetch.conf`. Provider tokens can be set via environment variables:
- `GH_TOKEN` for GitHub
- `GITLAB_TOKEN` for GitLab
- `GITEA_TOKEN` for Gitea
- `SOURCEHUT_TOKEN` for Sourcehut

Cache stored at `~/.local/share/gitfetch/cache.db` (SQLite).

## Testing

Tests use pytest with mocking for external API calls. Test files mirror source structure:
- `tests/test_cache.py` - Cache expiry, SQLite operations
- `tests/test_cli.py` - Argument parsing, initialization flow
- `tests/test_display.py` - Rendering, layout calculations
- `tests/test_fetcher.py` - Provider API mocking
- `tests/test_search_query.py` - GitHub search query parsing

## Dependencies

Python requires `requests`, `readchar`, `webcolors`. Dev dependencies include `pytest`, `black`, `mypy`.

Rust TUI requires `ratatui`, `crossterm`, `portable-pty`, `vt100`.
