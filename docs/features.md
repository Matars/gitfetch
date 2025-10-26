---
layout: default
title: Features
---

# Features

gitfetch provides a beautiful, neofetch-style display of your git hosting platform statistics with extensive customization options.

## Core Features

- **Neofetch-style display** with ASCII art
- **Comprehensive statistics** from multiple git hosting platforms
- **Smart SQLite-based caching** system for faster subsequent runs
- **Cross-platform support** (macOS and Linux)
- **First-run initialization** with interactive provider selection
- **Extensive customization** options for contribution characters, sections, and display elements

## Visual Customization

- Customize contribution block characters
- Hide/show specific sections (achievements, languages, issues, PRs, etc.)
- Control display dimensions and layout
- Simulate contribution-graph pixel art from text or predefined shapes

## Supported Platforms

- **GitHub** - Uses GitHub CLI (gh) for authentication
- **GitLab** - Uses GitLab CLI (glab) for authentication
- **Gitea/Forgejo/Codeberg** - Uses personal access tokens
- **Sourcehut** - Uses personal access tokens

## Advanced Options

- Repository-specific stats for local git repositories
- Cache management (bypass, clear)
- Provider switching
- Custom graph dimensions
- Layout control (spaced/not spaced)

## Intelligent Layout System

gitfetch automatically adapts to your terminal size:

- **Full Layout**: All sections when width ≥ 120 columns
- **Compact Layout**: Graph and key info side-by-side for medium terminals
- **Minimal Layout**: Contribution graph only for narrow terminals

The system considers both terminal width and height for optimal display.
