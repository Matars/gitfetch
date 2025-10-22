.PHONY: test install dev clean lint

# Install dependencies
install:
	pip install -r requirements.txt

# Install in development mode
dev:
	pip install -e .

# Run tests
test:
	python3 -m pytest tests/ -v

# Clean up cache and build files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
