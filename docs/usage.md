---
layout: default
title: Features & Usage
nav_order: 2
---

# Features & Usage

gitfetch brings the magic of neofetch to your git hosting platforms, displaying your coding activity in a stunning, colorful terminal interface that's both beautiful and highly customizable.

## 🚀 Core Features

- **Neofetch-style display** with stunning ASCII art that brings your stats to life
- **Comprehensive statistics** from GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut
- **Smart SQLite-based caching** system for lightning-fast subsequent runs
- **Cross-platform support** (macOS and Linux) - works wherever you code
- **View active pull requests and issues** - stay on top of your contributions
- **Display commit streak information** - track your coding momentum
- **Extensive customization** options that let you make it truly yours

## 🎨 Visual Customization

Transform your gitfetch display with powerful visual options:

- **Custom contribution characters** - use any symbol or emoji for your graph blocks
- **Dynamic section control** - hide/show achievements, languages, issues, PRs, and more
- **Flexible dimensions** - adjust width and height to fit your terminal perfectly
- **ASCII art simulation** - create pixel art from text or use predefined shapes like kitty, cat, heart, and star
- **Advanced color customization** with hex codes and predefined color schemes

## 🧠 Intelligent Layout System

gitfetch automatically adapts to your terminal environment:

- **Full Layout**: Complete information display when you have 120+ columns
- **Compact Layout**: Side-by-side graph and stats for medium terminals
- **Minimal Layout**: Clean contribution graph for narrow screens

The system intelligently considers both terminal width AND height to deliver the optimal viewing experience, no matter your setup.

## Basic Usage

Use default username (from config):

```bash
gitfetch
```

Fetch stats for specific user:

```bash
gitfetch username
```

## Repository-Specific Stats

Display contribution statistics for the current local git repository:

```bash
gitfetch --local
```

Shows commit activity over the last year, built from local git history

```bash
gitfetch --graph-timeline
```

Displays git commit timeline, built from local git history

**Current Limitations:**

- Only shows contribution graph and timeline
- No repository metadata (stars, forks, issues, etc.)
- No language statistics for the repository
- Limited to local git history analysis

## Configuration

Change the configured git provider:

```bash
gitfetch --change-provider
```

## Visual Customization

### Contribution Characters

```bash
gitfetch --custom-box "██"
gitfetch --custom-box "■"
gitfetch --custom-box "●"
gitfetch --custom-box "★"
gitfetch --custom-box "◆"
gitfetch --custom-box "◉"
```

### Predefined Shapes

```bash
gitfetch --shape kitty
gitfetch --shape heart_shiny
```

Display multiple shapes with vertical spacing:

```bash
gitfetch --shape kitty heart_shiny
gitfetch --shape heart kitty
```

#### Available Shapes

gitfetch includes the following predefined shapes:

- `kitty` - A cute cat face
- `oneup` - Classic Super Mario mushroom power-up
- `oneup2` - Alternative mushroom design
- `hackerschool` - Hacker School logo
- `octocat` - GitHub's Octocat mascot
- `octocat2` - Alternative Octocat design
- `hello` - "HELLO" text
- `heart1` - Simple heart shape
- `heart2` - Alternative heart design
- `heart` - Standard heart shape
- `heart_shiny` - Heart with sparkle effect
- `hireme` - "HIRE ME" text
- `beer` - Beer mug design
- `gliders` - Conway's Game of Life glider pattern

### Graph Dimensions

```bash
gitfetch --width 50 --height 5  # 50 chars wide, 5 days high
gitfetch --width 100            # Custom width, default height
gitfetch --height 3             # Default width, 3 days high
```

### Hide Elements

```bash
gitfetch --no-date              # Hide month/date labels
gitfetch --graph-only           # Show only contribution graph
gitfetch --no-achievements      # Hide achievements
gitfetch --no-languages         # Hide languages
gitfetch --no-issues            # Hide issues section
gitfetch --no-pr               # Hide pull requests
gitfetch --no-account          # Hide account info
gitfetch --no-grid             # Hide contribution grid
```

### Combined Options

```bash
gitfetch --no-date --no-achievements --custom-box "█" --width 60
```

## Cache Options

Bypass cache and fetch fresh data:

```bash
gitfetch username --no-cache
```

Clear cache:

```bash
gitfetch --clear-cache
```

## Layout Control

gitfetch automatically adapts to your terminal size, but you can control spacing:

```bash
gitfetch --spaced     # Enable spaced layout
gitfetch --not-spaced # Disable spaced layout
```

## Help

See all available options:

```bash
gitfetch --help
```
