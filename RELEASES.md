# Release Notes

## Version 1.0.20 - Multiple Providers & Enhanced Documentation

### 🚀 Major Features

#### Multi-Provider Support

- **GitHub**: Full support with GitHub CLI integration
- **GitLab**: Support via GitLab CLI (glab)
- **Gitea/Forgejo/Codeberg**: Direct API support with custom URLs
- **Sourcehut**: Direct API support for git.sr.ht

#### Interactive Provider Selection

- Replaced numbered menu with intuitive arrow-key navigation
- Visual feedback with filled circles (●) for selected options
- Keyboard shortcuts: ↑/↓ to navigate, Enter to select

### 📚 Documentation Improvements

#### New Documentation Structure

- Created dedicated `docs/` folder with comprehensive guides
- `docs/providers.md`: Detailed setup instructions for all supported providers
- `docs/colors.md`: Complete color customization reference with ANSI codes

#### Streamlined Configuration

- Simplified `gitfetch.conf` comments pointing to documentation
- Removed verbose inline documentation from config file
- Updated README with cleaner structure and references

### 🛠️ Technical Improvements

#### Dependencies

- Added `readchar` library for interactive keyboard input
- Updated packaging to include documentation files

#### Configuration Management

- Improved config file generation with clean formatting
- Fixed config duplication issues
- Better error handling for provider selection

#### Packaging Updates

- Updated Homebrew and AUR workflows to include new dependencies
- Automated dependency updates in release process

### 🐛 Bug Fixes

- Fixed config file value duplication on save
- Corrected brew upgrade command in version output
- Improved file handling in config save operations

### 📦 Installation

The new version includes all dependencies automatically:

```bash
# Homebrew
brew upgrade gitfetch

# pip
pip install --upgrade gitfetch

# AUR (Arch Linux)
yay -S gitfetch-python
```

### 🔄 Migration

#### For Existing Users

- Run `gitfetch` to reconfigure with new provider selection
- Config file will be updated automatically
- Cache will be preserved

#### Provider Setup

After upgrade, run `gitfetch` and select your preferred provider:

- GitHub users: Ensure `gh` CLI is authenticated
- GitLab users: Ensure `glab` CLI is authenticated
- Gitea/Forgejo/Codeberg users: Set custom API URL
- Sourcehut users: Configure API access

### 📖 Documentation Access

After installation, documentation is available locally:

- `docs/providers.md` - Provider configuration guide
- `docs/colors.md` - Color customization reference

### 🤝 Contributing

The codebase now supports easy addition of new providers. See `docs/providers.md` for implementation details.

---

**Full Changelog**: [Compare v1.0.18...v1.0.20](https://github.com/Matars/gitfetch/compare/v1.0.18...v1.0.20)
