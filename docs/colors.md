---
layout: default
title: Color Customization
nav_order: 7
---

# Color Customization

gitfetch lets you customize every color in the terminal output via `~/.config/gitfetch/gitfetch.conf`.

## Color Configuration

Colors are defined in the `[COLORS]` section of the config file:

```ini
[COLORS]
header  = #0366d6
accent  = #6f42c1
muted   = #586069
0       = #ebedf0   # Level 0 (no contributions)
1       = #9be9a8   # Level 1 (1-2 contributions)
2       = #40c463   # Level 2 (3-6 contributions)
3       = #30a14e   # Level 3 (7-12 contributions)
4       = #216e39   # Level 4 (13+ contributions)
```

## Available Color Keys

| Key | Purpose |
|-----|---------|
| `reset` | Reset color to default |
| `bold` | Bold text formatting |
| `dim` | Dim/dimmed text |
| `red` | Red accent |
| `green` | Green accent |
| `yellow` | Yellow accent |
| `blue` | Blue accent |
| `magenta` | Magenta accent |
| `cyan` | Cyan accent |
| `white` | White text |
| `orange` | Orange accent |
| `accent` | Primary accent color |
| `header` | Section headers |
| `muted` | Secondary/subtle text |
| `0` | Contribution level 0 (empty) |
| `1` | Contribution level 1 (light) |
| `2` | Contribution level 2 (medium) |
| `3` | Contribution level 3 (dark) |
| `4` | Contribution level 4 (darkest) |

## Color Input Formats

You can use:

- **Hex codes**: `#RRGGBB` (e.g. `#50FA7B`)
- **CSS color names**: `green`, `blue`, `rebeccapurple`, etc.

## Default Dark Theme

```ini
[COLORS]
reset   = #000000
bold    = #FFFFFF
dim     = #888888
red     = #FF5555
green   = #50FA7B
yellow  = #F1FA8C
blue    = #BD93F9
magenta = #FF79C6
cyan    = #8BE9FD
white   = #F8F8F2
orange  = #FFB86C
accent  = #FFFFFF
header  = #76D7A1
muted   = #44475A
0       = #ebedf0
1       = #9be9a8
2       = #40c463
3       = #30a14e
4       = #216e39
```

## Contribution Levels

The coloring thresholds follow GitHub's standard:

- **0 contributions**: Lightest color (Level 0)
- **1-2 contributions**: Light (Level 1)
- **3-6 contributions**: Medium (Level 2)
- **7-12 contributions**: Dark (Level 3)
- **13+ contributions**: Darkest (Level 4)
