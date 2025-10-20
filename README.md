# gitfetch

A neofetch-style CLI tool for GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut statistics. Display your profile and stats from various git hosting platforms in a beautiful, colorful terminal interface.

<img width="3024" height="1964" alt="image" src="https://github.com/user-attachments/assets/bbb18d5d-4787-4998-a352-e8f4e59642c0" />

<img width="3441" height="1441" alt="2025-10-20-143110_hyprshot" src="https://github.com/user-attachments/assets/ee31ebe3-257f-4aff-994e-fffd47b48fa1" />

## Features

- Neofetch-style display with ASCII art
- Comprehensive statistics from multiple git hosting platforms
- Smart SQLite-based caching system for faster subsequent runs
- Persistent configuration with default username support
- Cross-platform support (macOS and Linux)
- First-run initialization with interactive provider selection

## Supported Platforms

- **GitHub** - Uses GitHub CLI (gh) for authentication
- **GitLab** - Uses GitLab CLI (glab) for authentication
- **Gitea/Forgejo/Codeberg** - Uses personal access tokens
- **Sourcehut** - Uses personal access tokens

## Installation

`gitfetch` can be installed without any prerequisites. During first-run setup, you'll be guided to install and authenticate with the necessary CLI tools or provide access tokens for your chosen git hosting platform.

## First-run Setup

When you run `gitfetch` for the first time, you'll be prompted to:

1. **Choose your git hosting provider** (GitHub, GitLab, Gitea/Forgejo/Codeberg, or Sourcehut)
2. **Install required CLI tools** (if using GitHub or GitLab)
3. **Authenticate** with your chosen platform
4. **Configure access tokens** (if using Gitea/Forgejo/Codeberg or Sourcehut)

The setup process will provide helpful error messages and installation instructions if anything is missing.

## Installing `gitfetch`

### macOS (Homebrew)

```bash
brew tap matars/gitfetch
brew install matars/gitfetch/gitfetch
```

### Arch Linux (AUR)

```bash
yay -S gitfetch-python
```

Or with other AUR helpers:

```bash
paru -S gitfetch-python
trizen -S gitfetch-python
```

Or manual build:

```bash
git clone https://aur.archlinux.org/gitfetch-python.git
cd gitfetch-python
makepkg -si
```

### From the sources

1. Clone this repo
2. `cd` into the repo
3. Then type the below command

### With `pip`

```bash
pip install -e .
```

### With `uv`

```bash
uv tool install git+https://github.com/Matars/gitfetch
```

### With `pipx`

```bash
pipx install git+https://github.com/Matars/gitfetch
```

## First Run

On first run, gitfetch will initialize and ask you to configure your default GitHub username:

```bash
gitfetch
```

This creates:

- `~/.config/gitfetch/gitfetch.conf` - Configuration file
- `~/.local/share/gitfetch/cache.db` - SQLite cache database

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

## Configuration

Configuration file location: `~/.config/gitfetch/gitfetch.conf`

The configuration file is automatically created on first run. See `docs/providers.md` for detailed provider configuration and `docs/colors.md` for color customization options.

### [DEFAULT] Section

```ini
[DEFAULT]
username = yourusername
cache_expiry_hours = 24
provider = github
provider_url = https://api.github.com
```

- `username`: Your default username (automatically detected)
- `cache_expiry_hours`: How long to keep cached data (default: 24 hours)
- `provider`: Git hosting provider (github, gitlab, gitea, sourcehut)
- `provider_url`: API URL for the provider

### [COLORS] Section

gitfetch supports extensive color customization. All colors use ANSI escape codes. See `docs/colors.md` for detailed color configuration options.

````ini
```ini
[COLORS]
reset = \033[0m
bold = \033[1m
# ... color definitions ...
````

See `docs/colors.md` for detailed color configuration options and customization examples.

## Supported Providers

gitfetch supports multiple Git hosting platforms:

- **GitHub** - Uses GitHub CLI (gh) for authentication
- **GitLab** - Uses GitLab CLI (glab) for authentication
- **Gitea/Forgejo/Codeberg** - Direct API access with personal access tokens
- **Sourcehut** - Direct API access with personal access tokens

See `docs/providers.md` for detailed setup instructions for each provider.

## Caching

Cache database location: `~/.local/share/gitfetch/cache.db`

This follows XDG Base Directory specification for application data.

### Upgrading from older versions

If you have an older version of gitfetch that stored cache in `~/.config/gitfetch/cache.db`, you can safely delete the old cache file:

```bash
rm ~/.config/gitfetch/cache.db
```

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
