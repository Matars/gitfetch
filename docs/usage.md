---
layout: default
title: Usage
nav_order: 4
---

# Usage

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

## Cache Options

Bypass cache and fetch fresh data:

```bash
gitfetch username --no-cache
```

Clear cache:

```bash
gitfetch --clear-cache
```

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
```

### Predefined Shapes

```bash
gitfetch --shape kitty
gitfetch --shape cat
```

Display multiple shapes with vertical spacing:

```bash
gitfetch --shape kitty cat
gitfetch --shape heart star
```

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
