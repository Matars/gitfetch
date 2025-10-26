---
layout: default
title: Supported Providers
nav_order: 5
---

# Supported Providers

gitfetch supports multiple Git hosting platforms with different authentication methods.

## GitHub

**Authentication**: Uses GitHub CLI (gh)

**Setup**:

1. Install GitHub CLI: `brew install gh` (macOS) or follow [official instructions](https://cli.github.com/)
2. Run `gh auth login` to authenticate
3. gitfetch will detect and use your GitHub credentials

## GitLab

**Authentication**: Uses GitLab CLI (glab)

**Setup**:

1. Install GitLab CLI: `brew install glab` (macOS) or follow [official instructions](https://gitlab.com/gitlab-org/cli)
2. Run `glab auth login` to authenticate
3. gitfetch will detect and use your GitLab credentials

## Gitea/Forgejo/Codeberg

**Authentication**: Personal access tokens

**Setup**:

1. Generate a personal access token in your account settings
2. During gitfetch setup, select Gitea/Forgejo/Codeberg
3. Enter your instance URL and personal access token

**Supported Instances**:

- Gitea (any instance)
- Forgejo (any instance)
- Codeberg (codeberg.org)

## Sourcehut

**Authentication**: Personal access tokens

**Setup**:

1. Generate an OAuth2 personal access token in your [account settings](https://meta.sr.ht/oauth2)
2. During gitfetch setup, select Sourcehut
3. Enter your personal access token

## Provider Configuration

You can change your configured provider at any time:

```bash
gitfetch --change-provider
```

The provider setting is stored in your configuration file at `~/.config/gitfetch/gitfetch.conf`.
