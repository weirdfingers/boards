.PHONY: help install dev build test lint typecheck clean setup-python setup-node docker-up docker-down docker-logs docs docs-dev docs-build docs-serve install-backend install-frontend dev-backend dev-frontend build-backend build-frontend test-backend test-frontend lint-backend lint-frontend typecheck-backend typecheck-frontend clean-frontend

BACKEND_DIR := packages/backend
FRONTEND_FILTER := --filter=@weirdfingers/boards...

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install all dependencies (Python and Node)

setup-python: ## Install Python dependencies for all packages
	@echo "Setting up Python packages..."
	@for dir in packages/*/; do \
		if [ -f "$$dir/pyproject.toml" ] || [ -f "$$dir/setup.py" ] || [ -f "$$dir/requirements.txt" ]; then \
			echo "Setting up $$dir..."; \
			cd "$$dir" && \
			if [ ! -d ".venv" ]; then \
				echo "Creating virtual environment in $$dir"; \
				uv venv; \
			fi && \
			echo "Installing dependencies in $$dir"; \
			if [ -f "pyproject.toml" ]; then \
				uv pip install -e ".[dev]"; \
			elif [ -f "setup.py" ]; then \
				uv pip install -e .; \
			elif [ -f "requirements.txt" ]; then \
				uv pip install -r "requirements.txt"; \
			fi && \
			cd ..; \
		fi; \
	done

setup-node: ## Install Node dependencies for all packages
	@echo "Installing Node dependencies..."
	pnpm install

dev: ## Start development servers
	@echo "Starting development servers..."
	$(MAKE) -j2 dev-backend dev-frontend

build: build-backend build-frontend ## Build all packages

test: test-backend test-frontend ## Run all tests

lint: lint-backend lint-frontend ## Run linters

typecheck: typecheck-backend typecheck-frontend ## Run type checking

clean: clean-backend clean-frontend ## Clean all build artifacts and dependencies

install-backend: setup-python ## Install backend (Python) dependencies only

install-frontend: setup-node ## Install frontend (Node) dependencies only

dev-backend: ## Start backend development server only
	@echo "Starting backend server..."
	cd $(BACKEND_DIR) && uv run uvicorn boards.api.app:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend development servers only
	@echo "Starting frontend development servers..."
	@if command -v turbo > /dev/null 2>&1; then \
		pnpm turbo dev $(FRONTEND_FILTER); \
	else \
		echo "Turbo not found, running frontend package dev scripts individually..."; \
		pnpm --parallel $(FRONTEND_FILTER) dev; \
	fi

build-backend: ## Build backend (Python) only
	@echo "Building backend package..."
	cd $(BACKEND_DIR) && uv build

build-frontend: ## Build frontend (Node) only
	@echo "Building frontend packages..."
	pnpm turbo build $(FRONTEND_FILTER)

test-backend: ## Run backend (Python) tests only
	@echo "Running backend tests..."
	cd $(BACKEND_DIR) && uv run pytest tests/

test-frontend: ## Run frontend (Node) tests only
	@echo "Running frontend tests..."
	pnpm turbo test $(FRONTEND_FILTER)

lint-backend: ## Lint backend (Python) only
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && uv run ruff check . && uv run pyright

lint-frontend: ## Lint frontend (Node) only
	@echo "Linting frontend..."
	pnpm turbo lint $(FRONTEND_FILTER)

typecheck-backend: ## Typecheck backend (Python) only
	@echo "Type checking backend..."
	cd $(BACKEND_DIR) && uv run pyright

typecheck-frontend: ## Typecheck frontend (Node) only
	@echo "Type checking frontend..."
	pnpm turbo typecheck $(FRONTEND_FILTER)

clean-backend: ## Clean backend (Python) artifacts only
	@echo "Cleaning backend..."
	@find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

clean-frontend: ## Clean frontend (Node) artifacts only
	@echo "Cleaning frontend..."
	@find . -path "./$(BACKEND_DIR)" -prune -o -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -path "./$(BACKEND_DIR)" -prune -o -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@find . -path "./$(BACKEND_DIR)" -prune -o -type d -name ".turbo" -exec rm -rf {} + 2>/dev/null || true
	@rm -f pnpm-lock.yaml package-lock.json yarn.lock

docker-up: ## Start Docker services (databases, etc.)
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

docs: docs-dev ## Start documentation development server (alias)

docs-dev: ## Start documentation development server  
	@echo "Starting documentation development server..."
	cd apps/docs && pnpm start

docs-build: ## Build documentation for production
	@echo "Building documentation..."
	cd apps/docs && pnpm build

docs-serve: ## Serve built documentation
	@echo "Serving documentation..."
	cd apps/docs && pnpm serve

