# gitfetch

[![CI](https://github.com/Matars/gitfetch/actions/workflows/ci.yml/badge.svg)](https://github.com/Matars/gitfetch/actions/workflows/ci.yml)

A neofetch-style CLI tool for GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut statistics. Display your profile and stats from various git hosting platforms in a beautiful, colorful terminal interface with extensive customization options and intelligent layout adaptation.

> **Note**: This project is still maturing with only ~30 closed issues as of November 1st, 2025. If you encounter bugs, have feature requests, or want to contribute, please [open an issue](https://github.com/Matars/gitfetch/issues).

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

## Documentation

📖 [Full Documentation](https://matars.github.io/gitfetch/)

## Quick Install

### macOS (Homebrew)

```bash
brew tap matars/gitfetch
brew install gitfetch
```

### Arch Linux (AUR)

```bash
yay -S gitfetch-python
```

### From Source with pip

Make sure you have pip installed, then run:

```bash
git clone https://github.com/Matars/gitfetch.git
cd gitfetch
make dev
```

## Features

- Neofetch-style display with ASCII art
- Comprehensive statistics from multiple git hosting platforms
- Encourages maintaining commit streaks
- Get PR's and issues quick view in terminal
- Smart SQLite-based caching system
- Cross-platform support (macOS and Linux)
- Extensive customization options

## Supported Platforms

- **GitHub** - Uses GitHub CLI (gh) for authentication
- **GitLab** - Uses GitLab CLI (glab) for authentication
- **Gitea/Forgejo/Codeberg** - Uses personal access tokens
- **Sourcehut** - Uses personal access tokens

## Uninstall

```bash
brew uninstall gitfetch          # Homebrew
brew untap matars/gitfetch     # Homebrew tap
```

```bash
pip uninstall gitfetch          # pip
```

```bash
yay -R gitfetch-python          # AUR (yay)
```

## License

GPL-2.0
