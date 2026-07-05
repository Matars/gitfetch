---
layout: default
title: Development
nav_order: 6
---

# Development

This project uses a Makefile for common development tasks.

## Setup

```bash
make install  # Install runtime dependencies
make dev      # Install in development mode (editable install)
```

## Testing

```bash
make test     # Run tests with pytest
```

## Building Binaries

Standalone executables are built automatically on release via GitHub Actions.
To build locally:

```bash
pip install pyinstaller
pip install -e .
pyinstaller --onefile --name gitfetch --paths src run.py
```

## Development Workflow

1. Clone the repository
2. Run `make dev` to set up development environment
3. Make your changes
4. Run `make test` to ensure tests pass

## Project Structure

```
gitfetch/
├── .github/workflows/    # CI/CD workflows (ci, release, pages)
├── src/gitfetch/         # Main package
│   ├── __init__.py
│   ├── cli.py            # Command line interface
│   ├── config.py         # Configuration handling
│   ├── cache.py          # SQLite caching
│   ├── fetcher.py        # API data fetching
│   ├── display.py        # Terminal display logic
│   ├── providers.py      # Provider definitions
│   └── text_patterns.py  # ASCII art patterns
├── tests/                # Unit tests
├── docs/                 # Documentation site
├── run.py                # PyInstaller entry point
├── pyproject.toml        # Project configuration
├── setup.py              # Setup script
├── Makefile              # Development tasks
├── flake.nix / flake.lock # Nix flake
└── CHANGELOG.md          # Release changelog
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under GPL-2.0. See [LICENSE](../LICENSE) for details.
