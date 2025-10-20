# gitfetch

A neofetch-style CLI tool for GitHub statistics. Display your GitHub profile and stats in a beautiful, colorful terminal interface.

<img width="3024" height="1964" alt="image" src="https://github.com/user-attachments/assets/bbb18d5d-4787-4998-a352-e8f4e59642c0" />

<img width="3441" height="1441" alt="2025-10-20-143110_hyprshot" src="https://github.com/user-attachments/assets/ee31ebe3-257f-4aff-994e-fffd47b48fa1" />

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

See installation instructions at: https://github.com/cli/cli#installation


### macOS

```bash
brew install gh
gh auth login
```

### Linux

Then authenticate:

```bash
gh auth login
```

### Verify Installation

```bash
gh auth status
```

You should see: `✓ Logged in to github.com as YOUR_USERNAME`

## Installing `gitfetch`

### macOS (Homebrew)

```bash
brew tap matars/gitfetch
brew install matars/gitfetch/gitfetch
```

### Arch Linux (AUR)

## Note: currenly not working, use local installation - AUR packagte will be fixed soon

```bash
yay -S gitfetch
```

Or with other AUR helpers:

```bash
paru -S gitfetch
trizen -S gitfetch
```

Or manual build:

```bash
git clone https://aur.archlinux.org/gitfetch.git
cd gitfetch
makepkg -si
```

### From the sources

1. Clone this repo
2. `cd` into the repo
3. Then type the below command

### With `uv`

```bash
uv tool install git+https://github.com/Matars/gitfetch
```

### With `pipx`

```bash
pipx install git+https://github.com/Matars/gitfetch
```

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

## Configuration

Configuration file location: `~/.config/gitfetch/gitfetch.conf`

The configuration file is automatically created on first run and contains two main sections:

### [DEFAULT] Section

```ini
[DEFAULT]
username = yourusername
cache_expiry_hours = 24
```

- `username`: Your default GitHub username (automatically set from authenticated GitHub CLI user)
- `cache_expiry_hours`: How long to keep cached data (default: 24 hours)

### [COLORS] Section

gitfetch supports extensive color customization. All colors use ANSI escape codes.

```ini
[COLORS]
reset = \033[0m
bold = \033[1m
dim = \033[2m
red = \033[91m
green = \033[92m
yellow = \033[93m
blue = \033[94m
magenta = \033[95m
cyan = \033[96m
white = \033[97m
orange = \033[38;2;255;165;0m
accent = \033[1m
header = \033[38;2;118;215;161m
muted = \033[2m
0 = \033[48;5;238m
1 = \033[48;5;28m
2 = \033[48;5;34m
3 = \033[48;5;40m
4 = \033[48;5;82m
```

#### Color Reference

- **Text Styles**:

  - `reset`: Reset all formatting
  - `bold`: Bold text
  - `dim`: Dimmed text
  - `accent`: Accent styling (bold)

- **Basic Colors**:

  - `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`: Standard ANSI colors
  - `orange`: Custom orange color

- **UI Elements**:

  - `header`: Section headers and main display text
  - `muted`: Separators and underlines

- **Contribution Graph**:
  - `0`: No contributions (lightest)
  - `1`: 1-2 contributions
  - `2`: 3-6 contributions
  - `3`: 7-12 contributions
  - `4`: 13+ contributions (darkest)

#### Customizing Colors

To change colors, edit `~/.config/gitfetch/gitfetch.conf` and modify the ANSI escape codes:

**Example: Change header color to blue**

```ini
header = \033[94m
```

**Example: Change contribution graph colors to a purple theme**

```ini
0 = \033[48;5;235m  # Dark gray for no contributions
1 = \033[48;5;60m   # Dark purple
2 = \033[48;5;62m   # Medium purple
3 = \033[48;5;64m   # Light purple
4 = \033[48;5;66m   # Bright purple
```

**Common ANSI Color Codes**:

- `\033[91m` = Bright Red
- `\033[92m` = Bright Green
- `\033[93m` = Bright Yellow
- `\033[94m` = Bright Blue
- `\033[95m` = Bright Magenta
- `\033[96m` = Bright Cyan
- `\033[97m` = Bright White

**Background Colors** (for contribution blocks):

- `\033[48;5;{color_code}m` where color_code is 0-255 (256-color palette)

Changes take effect immediately - no restart required.

## Caching

Cache database location: `~/.config/gitfetch/cache.db`

This will be moved in the future to a more standard location based on OS conventions.
This will also come with a gitfetch --migrate-cache command to migrate existing cache to the new location.

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
