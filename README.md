# gitfetch

[![CI](https://github.com/Matars/gitfetch/actions/workflows/ci.yml/badge.svg)](https://github.com/Matars/gitfetch/actions/workflows/ci.yml)

A neofetch-style CLI tool for GitHub, GitLab, Gitea, Forgejo, Codeberg, and Sourcehut statistics. Display your profile and stats from various git hosting platforms in a beautiful, colorful terminal interface with extensive customization options and intelligent layout adaptation.

> **Note**: This project is still maturing. If you encounter bugs, have feature requests, or want to contribute, please [open an issue](https://github.com/Matars/gitfetch/issues).

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

### Standalone Binary

Download from the [latest release](https://github.com/Matars/gitfetch/releases/latest):

| Platform | Asset |
|----------|-------|
| Linux x86_64 | `gitfetch-linux-x86_64` |
| macOS (Apple Silicon) | `gitfetch-macos-arm64` |
| Windows x86_64 | `gitfetch-windows-x86_64.exe` |

```bash
chmod +x gitfetch-*
./gitfetch-linux-x86_64
```

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

```bash
git clone https://github.com/Matars/gitfetch.git
cd gitfetch
make dev
```

## Features

- Neofetch-style display with ASCII art
- Comprehensive statistics from multiple git hosting platforms
- Encourages maintaining commit streaks
- Get PRs and issues quick view in terminal
- Local repository analysis (`gitfetch --local`)
- Git timeline view (`gitfetch --graph-timeline`)
- Text and shape simulation (`--text`, `--shape`)
- Smart SQLite-based caching system
- Cross-platform support (macOS, Linux, Windows)
- Extensive customization options

## Supported Platforms

- **GitHub** - Uses GitHub CLI (gh) or personal access token
- **GitLab** - Uses GitLab CLI (glab) or personal access token
- **Gitea/Forgejo/Codeberg** - Uses personal access tokens
- **Sourcehut** - Uses personal access tokens

## Uninstall

```bash
# Standalone binary
rm gitfetch-linux-x86_64

# Homebrew
brew uninstall gitfetch
brew untap matars/gitfetch

# pip
pip uninstall gitfetch

# AUR
yay -R gitfetch-python
```

## License

GPL-2.0
