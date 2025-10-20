"""
gitfetch - A neofetch-style CLI tool for GitHub statistics
"""

import re
from pathlib import Path


def _get_version() -> str:
    """Get version from package metadata or pyproject.toml."""
    try:
        # Try to get version from package metadata
        from importlib import metadata
        return metadata.version("gitfetch")
    except (ImportError, metadata.PackageNotFoundError):
        pass
    
    # Fallback: try to read from pyproject.toml (works in development)
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1)
    except (FileNotFoundError, OSError):
        pass
    return "unknown"


__version__ = _get_version()
