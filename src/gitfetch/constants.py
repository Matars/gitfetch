"""
Constants for gitfetch.

This module contains magic values and configuration constants
used throughout the application, making them easier to maintain
and modify in one place.
"""

# API timeouts (in seconds)
API_TIMEOUT_SHORT = 5
API_TIMEOUT_MEDIUM = 10
API_TIMEOUT_LONG = 30
API_TIMEOUT_RELEASE = 3

# Cache defaults
DEFAULT_CACHE_EXPIRY_MINUTES = 15
MAX_CACHE_EXPIRY_MINUTES = 1440  # 24 hours

# Pagination
REPOS_PER_PAGE = 100
SEARCH_RESULTS_PER_PAGE = 5

# Contribution graph defaults
DAYS_TO_SHOW = 7  # Days in a week for graph display

# Spinner timeout
SPINNER_THREAD_JOIN_TIMEOUT = 0.5

# Rate limit warning thresholds (percentage)
RATE_LIMIT_WARNING_THRESHOLD = 80
RATE_LIMIT_CRITICAL_THRESHOLD = 90

# Contribution display thresholds
TOTAL_CONTRIBUTIONS_LARGE = 10000

# Display formatting
DISPLAY_OFFSET_MIN = 80
