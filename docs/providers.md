# Git Providers

gitfetch supports multiple Git hosting providers. Configure your preferred provider in the config file.

## Supported Providers

### GitHub

- **provider**: `github`
- **provider_url**: `https://api.github.com`
- **Requirements**: GitHub CLI (`gh`) must be installed and authenticated
- **Authentication**: Run `gh auth login`

### GitLab

- **provider**: `gitlab`
- **provider_url**: `https://gitlab.com`
- **Requirements**: GitLab CLI (`glab`) must be installed and authenticated
- **Authentication**: Run `glab auth login`

### Gitea/Forgejo/Codeberg

- **provider**: `gitea`
- **provider_url**: Custom URL (e.g., `https://codeberg.org`, `https://gitea.com`)
- **Requirements**: None (uses API directly)
- **Authentication**: Set personal access token in environment or use CLI tools

### Sourcehut

- **provider**: `sourcehut`
- **provider_url**: `https://git.sr.ht`
- **Requirements**: None (uses API directly)
- **Authentication**: Set personal access token in environment

## Configuration

Set the provider and URL in your `gitfetch.conf`:

```ini
[DEFAULT]
provider = github
provider_url = https://api.github.com
```

## Adding New Providers

To add support for a new Git provider, implement a new fetcher class in `fetcher.py` and update the provider selection logic in `cli.py`.
