"""
Provider definitions and configuration for gitfetch.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProviderType(Enum):
    """Supported git hosting providers."""
    GITHUB = "github"
    GITLAB = "gitlab"
    GITEA = "gitea"
    SOURCEHUT = "sourcehut"


# Environment variable names for each provider's token
PROVIDER_ENV_VARS = {
    "github": "GH_TOKEN",
    "gitlab": "GITLAB_TOKEN",
    "gitea": "GITEA_TOKEN",
    "sourcehut": "SOURCEHUT_TOKEN",
}

# Default URLs for providers
PROVIDER_DEFAULT_URLS = {
    "github": "https://api.github.com",
    "gitlab": "https://gitlab.com",
    "sourcehut": "https://git.sr.ht",
    # gitea requires user-provided URL
}


@dataclass
class ProviderConfig:
    """Configuration for a git provider."""
    name: str
    username: str
    url: str
    token: str = ""

    @property
    def token_env_var(self) -> str:
        """Get the environment variable name for this provider's token."""
        return PROVIDER_ENV_VARS.get(self.name, "")

    @property
    def default_url(self) -> Optional[str]:
        """Get the default URL for this provider, if any."""
        return PROVIDER_DEFAULT_URLS.get(self.name)

    def has_token(self) -> bool:
        """Check if a token is configured."""
        return bool(self.token)
