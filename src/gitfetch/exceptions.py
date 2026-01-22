"""
Custom exceptions for gitfetch.

This module defines all custom exception classes used throughout
the application, providing better error handling and user experience.
"""


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
