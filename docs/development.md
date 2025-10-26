---
layout: default
title: Development
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

## Development Workflow

1. Clone the repository
2. Run `make dev` to set up development environment
3. Make your changes
4. Run `make test` to ensure tests pass

## Project Structure

```
gitfetch/
├── src/gitfetch/          # Main package
│   ├── __init__.py
│   ├── cli.py            # Command line interface
│   ├── config.py         # Configuration handling
│   ├── cache.py          # SQLite caching
│   ├── fetcher.py        # API data fetching
│   ├── display.py        # Terminal display logic
│   └── text_patterns.py  # ASCII art patterns
├── tests/                # Unit tests
├── pyproject.toml        # Project configuration
├── setup.py             # Setup script
└── Makefile             # Development tasks
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
