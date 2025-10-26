---
layout: default
title: Configuration
nav_order: 5
---

# Configuration

Configuration file location: `~/.config/gitfetch/gitfetch.conf`

The configuration file is automatically created on first run.

## [DEFAULT] Section

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

## [COLORS] Section

gitfetch supports extensive color customization using hex color codes or predefined color names.

### Available Colors

- **Text formatting**: `reset`, `bold`, `dim`
- **Basic colors**: `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`
- **Special colors**: `orange`, `accent`, `header`, `muted`
- **Contribution graph levels**: `0` (lowest) to `4` (highest)

### Example Configuration

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

### Supported Color Names and Hex Codes

See the full list in the [colors documentation](colors.md).

## Layout Control

gitfetch automatically adapts to your terminal size, but you can control spacing:

```bash
gitfetch --spaced     # Enable spaced layout
gitfetch --not-spaced # Disable spaced layout
```

## Custom Dimensions and Coloring Accuracy

The coloring system uses GitHub's standard contribution levels:

- **0 contributions**: Lightest gray
- **1-2 contributions**: Light green (Level 1)
- **3-6 contributions**: Medium green (Level 2)
- **7-12 contributions**: Dark green (Level 3)
- **13+ contributions**: Darkest green (Level 4)

Custom dimensions (`--width`, `--height`) control how many weeks/days are visible, but the coloring thresholds remain the same.

## Intelligent Layout System

gitfetch automatically selects the best layout based on your terminal dimensions:

- **Full Layout**: Shows all sections when width ≥ 120 columns
- **Compact Layout**: Shows graph and key info side-by-side for medium terminals
- **Minimal Layout**: Shows only the contribution graph for narrow terminals

The system considers both terminal width AND height to ensure optimal display.
