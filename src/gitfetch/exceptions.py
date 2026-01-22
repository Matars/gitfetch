"""
Custom exceptions for gitfetch.

This module defines all custom exception classes used throughout
the application, providing better error handling and user experience.
"""

import re


def redact_sensitive_info(text: str, tokens: list[str] | None = None) -> str:
    """
    Redact sensitive information (tokens, passwords) from error messages.

    Args:
        text: The text to redact sensitive information from
        tokens: Optional list of tokens to redact (will also detect common patterns)

    Returns:
        Text with sensitive information redacted
    """
    if not text:
        return text

    redacted = text

    # Redact tokens if provided
    if tokens:
        for token in tokens:
            if token and len(token) > 4:
                # Redact most of the token, keeping first 4 and last 4 chars
                if len(token) <= 8:
                    redacted = redacted.replace(token, "****")
                else:
                    redacted = redacted.replace(token, f"{token[:4]}...{token[-4:]}")

    # Redact common sensitive patterns in URLs and headers
    # Pattern: Bearer/GitHub/Basic tokens in URLs or headers
    patterns_to_redact = [
        (r'(Bearer|GitHub|token|Basic)\s+[a-zA-Z0-9_\-\.]{20,}', r'\1 ****'),
        (r'authorization["\']?\s*:\s*["\']?[a-zA-Z0-9_\-\.]{20,}', 'authorization: ****'),
        (r'token["\']?\s*:\s*["\']?[a-zA-Z0-9_\-\.]{20,}', 'token: ****'),
    ]

    for pattern, replacement in patterns_to_redact:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    return redacted


class GitfetchException(Exception):
    """Base exception for all gitfetch errors."""

    def __init__(self, message: str, hint: str = ""):
        """
        Initialize the exception.

        Args:
            message: Error message describing the problem
            hint: Optional hint for the user on how to fix the issue
        """
        super().__init__(message)
        self.hint = hint

    def __str__(self) -> str:
        msg = super().__str__()
        if self.hint:
            return f"{msg}\n  Hint: {self.hint}"
        return msg


class AuthenticationError(GitfetchException):
    """Raised when authentication fails (invalid token, not logged in, etc.)."""

    def __init__(self, message: str = "Authentication failed", hint: str = ""):
        super().__init__(message, hint or "Try running 'gh auth login' for GitHub")


class RateLimitError(GitfetchException):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str = "API rate limit exceeded", hint: str = ""):
        super().__init__(message, hint or "Wait a few minutes before trying again")


class UserNotFoundError(GitfetchException):
    """Raised when a user cannot be found on the specified platform."""

    def __init__(self, username: str, platform: str = "GitHub"):
        message = f"User '{username}' not found on {platform}"
        hint = f"Verify the username is correct for {platform}"
        super().__init__(message, hint)


class APIError(GitfetchException):
    """Raised when an API request fails (network issues, server errors, etc.)."""

    def __init__(self, message: str = "API request failed", hint: str = ""):
        super().__init__(message, hint or "Check your network connection and try again")


class ConfigurationError(GitfetchException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str = "Configuration error", hint: str = ""):
        super().__init__(message, hint or "Check your configuration file")


class CacheError(GitfetchException):
    """Raised when cache operations fail."""

    def __init__(self, message: str = "Cache error", hint: str = ""):
        super().__init__(message, hint or "Try clearing the cache with --no-cache")
