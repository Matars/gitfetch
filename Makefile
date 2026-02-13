.PHONY: test install dev clean lint test-aur test-homebrew test-ci test-all

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

test-aur:
	act -j update-aur --container-architecture linux/amd64 --secret AUR_SSH_KEY="$$(cat ~/.ssh/aur_key)"

test-homebrew:
	act -j update-homebrew --container-architecture linux/amd64 --secret HOMEBREW_TAP_TOKEN="$$(gh auth token)"

test-ci:
	act push --container-architecture linux/amd64

test-all:
	act --container-architecture linux/amd64
