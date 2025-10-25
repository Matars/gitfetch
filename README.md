# gitfetch

A neofetch-style CLI tool for GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut statistics. Display your profile and stats from various git hosting platforms in a beautiful, colorful terminal interface with extensive customization options and intelligent layout adaptation.

<table>
  <tr>
    <td>
      <img width="3024" height="1964" alt="image" src="https://github.com/user-attachments/assets/bbb18d5d-4787-4998-a352-e8f4e59642c0" />
    </td>
    <td>
      <img width="3012" height="1982" alt="image" src="https://github.com/user-attachments/assets/6d061c76-3e45-47c3-989f-0776be6cf846" />
    </td>
  </tr>
</table>

<img width="3441" height="1441" alt="2025-10-20-143110_hyprshot" src="https://github.com/user-attachments/assets/ee31ebe3-257f-4aff-994e-fffd47b48fa1" />

## Features

- Neofetch-style display with ASCII art
- Comprehensive statistics from multiple git hosting platforms
- Smart SQLite-based caching system for faster subsequent runs
- Cross-platform support (macOS and Linux)
- First-run initialization with interactive provider selection
- Customize contribution characters, hide/show sections, control display elements
- Simulate contribution-graph pixel art from text using `--text "Your Text"` or predefined shapes using `--shape KITTY` (visual simulation only — does not create commits). This feature was inspired by and borrows the visual approach from gelstudios/gitfiti.
- Flags for advanced configuration (e.g., `--no-date`, `--graph-only`, `--custom-box`, `--width`, `--height`) see full list below with `gitfetch --help`

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
brew install gitfetch
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

### NixOS (Flake only)

Add input to the flake:
```nix
gitfetch.url = "github:Matars/gitfetch"
```
And in ``environment.SystemPackages`` add:
```nix
inputs.gitfetch.packages.${system}.default
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

## Development

This project uses a Makefile for common development tasks. After cloning the repository, you can use these make commands:

### Setup

```bash
make install  # Install runtime dependencies
make dev      # Install in development mode (editable install)
```

### Testing

```bash
make test     # Run tests with pytest
```

### Development Workflow

1. Clone the repository
2. Run `make dev` to set up development environment
3. Make your changes
4. Run `make test` to ensure tests pass

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

### Repository-Specific Stats

Display contribution statistics for the current local git repository:

```bash
gitfetch --local
```

Shows commit activity over the last year, built from local git history

```bash
gitfetch --graph-timeline
```

Displays git commit timeline, build from local git history

**Current Limitations:**

- Only shows contribution graph and timeline
- No repository metadata (stars, forks, issues, etc.)
- No language statistics for the repository
- Limited to local git history analysis

If you would like to expand this feature and and parse more repository data, please open an issue or submit a PR!

### Cache Options

Bypass cache and fetch fresh data:

```bash
gitfetch username --no-cache
```

Clear cache:

```bash
gitfetch --clear-cache
```

### Configuration

Change the configured git provider:

```bash
gitfetch --change-provider
```

### Visual Customization

Customize contribution block characters:

```bash
gitfetch --custom-box "██"
gitfetch --custom-box "■"
gitfetch --custom-box "●"
```

Set custom graph dimensions:

```bash
gitfetch --width 50 --height 5  # 50 chars wide, 5 days high
gitfetch --width 100            # Custom width, default height
gitfetch --height 3             # Default width, 3 days high
```

Hide month/date labels:

```bash
gitfetch --no-date
```

Show only contribution graph:

```bash
gitfetch --graph-only
```

Hide specific sections:

```bash
gitfetch --no-achievements  # Hide achievements
gitfetch --no-languages     # Hide languages
gitfetch --no-issues        # Hide issues section
gitfetch --no-pr           # Hide pull requests
gitfetch --no-account      # Hide account info
gitfetch --no-grid         # Hide contribution grid
```

Combine multiple options:

```bash
gitfetch --no-date --no-achievements --custom-box "█" --width 60
```

## Configuration

Configuration file location: `~/.config/gitfetch/gitfetch.conf`

The configuration file is automatically created on first run. See `docs/providers.md` for detailed provider configuration and `docs/colors.md` for color customization options.

### [DEFAULT] Section

```ini
[DEFAULT]
username = yourusername
cache_expiry_minutes = 15
provider = github
provider_url = https://api.github.com
custom_box = ■
```

- `username`: Your default username (automatically detected)
- `cache_expiry_minutes`: How long to keep cached data (default: 15 minutes)
- `provider`: Git hosting provider (github, gitlab, gitea, sourcehut)
- `provider_url`: API URL for the provider
- `custom_box`: Character used for contribution blocks (default: ■)

**Note**: Custom graph dimensions (`--width`, `--height`) and section visibility flags (`--no-*`) are command-line only and not saved in the configuration file.
However if there is a need for it to be added to the config file please open an issue.

### [COLORS] Section

gitfetch supports extensive color customization using hex color codes or predefined color names.

#### Available Colors

- **Text formatting**: `reset`, `bold`, `dim`
- **Basic colors**: `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`
- **Special colors**: `orange`, `accent`, `header`, `muted`
- **Contribution graph levels**: `0` (lowest) to `4` (highest)

#### Example Configuration

```ini
[COLORS]
header = #0366d6
accent = #6f42c1
muted = #586069
0 = #ebedf0  # Light gray background
1 = #9be9a8  # Light green background
2 = #40c463  # Medium green
3 = #30a14e  # Dark green
4 = #216e39  # Darkest green
```

See `docs/colors.md` for the complete list of supported color names and hex codes.

### Layout Control

gitfetch automatically adapts to your terminal size, but you can control spacing:

```bash
gitfetch --spaced     # Enable spaced layout
gitfetch --not-spaced # Disable spaced layout
```

### Custom Dimensions and Coloring Accuracy

The coloring system uses GitHub's standard contribution levels, which are absolute thresholds that remain consistent regardless of the time period or dimensions displayed:

- **0 contributions**: Lightest gray
- **1-2 contributions**: Light green (Level 1)
- **3-6 contributions**: Medium green (Level 2)
- **7-12 contributions**: Dark green (Level 3)
- **13+ contributions**: Darkest green (Level 4)

**What Custom Dimensions Affect:**

- `--width` and `--height` control how many weeks/days are visible
- The coloring thresholds remain the same (GitHub standard)
- You see the same accurate representation, just for a different time period

**When It Might Seem "Inaccurate":**
If you're viewing only recent weeks with generally lower activity, everything might appear in lighter colors. This is actually correct - those weeks truly have fewer contributions compared to your overall history standards.

## Intelligent Layout System

gitfetch automatically selects the best layout based on your terminal dimensions:

- **Full Layout**: Shows all sections (graph, account info, languages, achievements) when there's sufficient space (width ≥ 120 columns)
- **Compact Layout**: Shows graph and key info side-by-side for medium terminals
- **Minimal Layout**: Shows only the contribution graph for narrow terminals

The system considers both terminal width AND height to ensure optimal display. For very short terminals, it may choose more compact layouts even with sufficient width.

You can override automatic layout selection using the `--width` and `--height` flags to set custom graph dimensions, which will force gitfetch to adapt the layout accordingly.

## Supported Providers

gitfetch supports multiple Git hosting platforms:

See `docs/providers.md` for detailed setup instructions for each provider.

## Caching

Cache database location: `~/.local/share/gitfetch/cache.db`

### Upgrading from older versions

If you have an older version of gitfetch (pre v1.1.0) that stored cache in `~/.config/gitfetch/cache.db`, you can safely delete the old cache file:

```bash
rm ~/.config/gitfetch/cache.db
```

## Acknowledgements

- Inspired by the beautiful contribution graph design from [Kusa](https://github.com/Ryu0118/Kusa) by Ryu0118
- Inspired by the very cool and extremely fun tool [songfetch](https://github.com/fwtwoo/songfetch) by fwtwoo
- The `--text` contribution-graph simulation feature takes inspiration from and adapts ideas from [gelstudios/gitfiti](https://github.com/gelstudios/gitfiti) — credit to the project for the concept of painting the contribution calendar (this implementation only simulates the appearance and does not modify git history).

### Contributers

- ilonic23: Added nix packaging
- quunarc: small code refactoring
- Zeviraty: Small fixes, color configuration
- Vaishnav-Sabari-Girish: Better installation instructions
- Noirbizzarre: Added installation instructions using uv and pipx
- Fwtwoo: readme update
- Joeliscoding: Added homebrew formula and fixed readme

## License

GPL-2.0
