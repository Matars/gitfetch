# gitfetch

<img width="3024" height="1964" alt="image" src="https://github.com/user-attachments/assets/bbb18d5d-4787-4998-a352-e8f4e59642c0" />

A neofetch-style CLI tool for GitHub statistics. Display your GitHub profile and stats in a beautiful, colorful terminal interface.

## Features

- Neofetch-style display with ASCII art
- Comprehensive GitHub statistics
- Smart SQLite-based caching system for faster subsequent runs
- Persistent configuration with default username support
- Uses GitHub CLI (gh) for authentication - no rate limits!
- Cross-platform support (macOS and Linux)
- First-run initialization with interactive setup

## Prerequisites

**GitHub CLI (gh) must be installed and authenticated:**

### macOS

```bash
brew install gh
gh auth login
```

### Linux

See installation instructions at: https://github.com/cli/cli#installation

Then authenticate:

```bash
gh auth login
```

### Verify Installation

```bash
gh auth status
```

You should see: `✓ Logged in to github.com as YOUR_USERNAME`

## Installation

```bash
pip install -e .
```

## First Run

On first run, gitfetch will initialize and ask you to configure your default GitHub username:

```bash
gitfetch
```

This creates:

- `~/.config/gitfetch/gitfetch.conf` - Configuration file
- `~/.config/gitfetch/cache.db` - SQLite cache database

## Usage

Use default username (from config):

```bash
gitfetch
```

Fetch stats for specific user:

```bash
gitfetch username
```

Bypass cache and fetch fresh data:

```bash
gitfetch username --no-cache
```

Clear cache:

```bash
gitfetch --clear-cache
```

## Troubleshooting

### Error: GitHub CLI is not authenticated

```bash
gh auth login
```

Follow the prompts to authenticate with GitHub.

### Error: GitHub CLI (gh) is not installed

Install GitHub CLI:

- **macOS**: `brew install gh`
- **Linux**: See https://github.com/cli/cli#installation

### Check Authentication Status

```bash
gh auth status
```

## Project Structure

```
gitfetch/
├── src/
│   └── gitfetch/
│       ├── __init__.py      # Package initialization
│       ├── cli.py           # Command-line interface
│       ├── fetcher.py       # GitHub API data fetching
│       ├── display.py       # Display formatting
│       ├── cache.py         # SQLite cache management
│       └── config.py        # Configuration management
├── tests/
│   ├── test_fetcher.py      # Fetcher unit tests
│   ├── test_cache.py        # Cache unit tests
│   └── test_config.py       # Config unit tests
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## Configuration

Configuration file location: `~/.config/gitfetch/gitfetch.conf`

Example configuration:

```ini
[DEFAULT]
username = yourusername
cache_expiry_hours = 6
```

Cache database location: `~/.config/gitfetch/cache.db`

## Why GitHub CLI?

Using the GitHub CLI (gh) instead of direct API calls provides several benefits:

- ✅ **No rate limits** - Uses your authenticated GitHub account
- ✅ **Automatic authentication** - No need to manage tokens
- ✅ **Better security** - Credentials managed by gh CLI
- ✅ **Simpler setup** - Just run `gh auth login`

## Acknowledgements

- Inspired by the beautiful contribution graph design from [Kusa](https://github.com/Ryu0118/Kusa) by Ryu0118.
- Inspired by the very cool and extremely fun tool [songfetch](https://github.com/fwtwoo/songfetch) by fwtwoo.

## License

GPL-2.0
