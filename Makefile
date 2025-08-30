.PHONY: help install dev build test lint typecheck clean setup-python setup-node docker-up docker-down docker-logs

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: setup-python setup-node ## Install all dependencies (Python and Node)

setup-python: ## Install Python dependencies for all packages
	@echo "Setting up Python packages..."
	@for dir in packages/*/; do \
		if [ -f "$$dir/pyproject.toml" ] || [ -f "$$dir/setup.py" ] || [ -f "$$dir/requirements.txt" ]; then \
			echo "Installing $$dir..."; \
			if [ -f "$$dir/pyproject.toml" ]; then \
				cd "$$dir" && uv pip install -e .; \
			elif [ -f "$$dir/setup.py" ]; then \
				cd "$$dir" && uv pip install -e .; \
			elif [ -f "$$dir/requirements.txt" ]; then \
				uv pip install -r "$$dir/requirements.txt"; \
			fi; \
		fi; \
	done

setup-node: ## Install Node dependencies for all packages
	@echo "Installing Node dependencies..."
	pnpm install

dev: ## Start development servers
	@echo "Starting development servers..."
	@if command -v turbo > /dev/null 2>&1; then \
		pnpm turbo dev; \
	else \
		echo "Turbo not found, running package dev scripts individually..."; \
		pnpm --parallel dev; \
	fi

build: ## Build all packages
	@echo "Building all packages..."
	@# Build Python packages
	@for dir in packages/*/; do \
		if [ -f "$$dir/pyproject.toml" ] || [ -f "$$dir/setup.py" ]; then \
			echo "Building Python package in $$dir..."; \
			cd "$$dir" && uv build; \
		fi; \
	done
	@# Build Node packages
	pnpm turbo build

test: ## Run all tests
	@echo "Running tests..."
	@# Test Python packages
	@for dir in packages/*/; do \
		if [ -f "$$dir/pyproject.toml" ] || [ -f "$$dir/setup.py" ]; then \
			if [ -d "$$dir/tests" ]; then \
				echo "Testing Python package in $$dir..."; \
				cd "$$dir" && uv run pytest tests/; \
			fi; \
		fi; \
	done
	@# Test Node packages
	pnpm turbo test

lint: ## Run linters
	@echo "Running linters..."
	@# Lint Python packages
	@for dir in packages/*/; do \
		if [ -f "$$dir/pyproject.toml" ] || [ -f "$$dir/setup.py" ]; then \
			echo "Linting Python package in $$dir..."; \
			cd "$$dir" && uv run ruff check . && uv run mypy .; \
		fi; \
	done
	@# Lint Node packages
	pnpm turbo lint

typecheck: ## Run type checking
	@echo "Running type checking..."
	@# Python type checking (handled in lint)
	@# Node type checking
	pnpm turbo typecheck

clean: ## Clean all build artifacts and dependencies
	@echo "Cleaning workspace..."
	@# Clean Python packages
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@# Clean Node packages
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".turbo" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf pnpm-lock.yaml package-lock.json yarn.lock

docker-up: ## Start Docker services (databases, etc.)
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f