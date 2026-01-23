.PHONY: help install dev build test lint typecheck format clean setup-python setup-node docker-up docker-down docker-logs docs dev-docs docs-build docs-serve install-backend install-frontend dev-backend dev-frontend build-backend build-frontend test-backend test-frontend lint-backend lint-frontend typecheck-backend typecheck-frontend format-backend format-frontend clean-backend clean-frontend

BACKEND_DIR := packages/backend
FRONTEND_FILTER := --filter=@weirdfingers/boards... --filter=@weirdfingers/boards-auth-clerk... --filter=@weirdfingers/boards-auth-jwt... --filter=@weirdfingers/boards-auth-supabase... --filter=baseboards...  --filter=@weirdfingers/baseboards...
DEV_FRONTEND_FILTER := --filter=@weirdfingers/boards... --filter=@weirdfingers/boards-auth-clerk... --filter=@weirdfingers/boards-auth-jwt... --filter=@weirdfingers/boards-auth-supabase... --filter=baseboards...


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

format: format-backend format-frontend ## Format all code (Python and Node)

clean: clean-backend clean-frontend ## Clean all build artifacts and dependencies

install-backend: setup-python ## Install backend (Python) dependencies only

install-frontend: setup-node ## Install frontend (Node) dependencies only

dev-backend: ## Start backend development server only
	@echo "Starting backend server..."
	cd $(BACKEND_DIR) && uv run boards-server serve --reload --log-level debug

dev-worker: ## Start background worker (development)
	@echo "Starting background worker..."
	cd $(BACKEND_DIR) && uv run boards-worker --log-level debug --processes=1 --threads=1

dev-worker-watch: ## Start background worker with auto-reload using entr (requires: brew install entr)
	@echo "Starting background worker with auto-reload (Press Ctrl+C to stop)..."
	@if ! command -v entr > /dev/null 2>&1; then \
		echo "Error: entr is not installed. Install with: brew install entr"; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && while sleep 0.1; do find src -name '*.py' | entr -drz uv run boards-worker --log-level debug --processes=1 --threads=1 || exit 0; done

dev-frontend: ## Start frontend development servers only
	@echo "Starting frontend development servers..."
	@if command -v turbo > /dev/null 2>&1; then \
		pnpm turbo dev $(DEV_FRONTEND_FILTER); \
	else \
		echo "Turbo not found, running frontend package dev scripts individually..."; \
		pnpm --parallel $(DEV_FRONTEND_FILTER) dev; \
	fi

build-backend: ## Build backend (Python) only
	@echo "Building backend package..."
	cd $(BACKEND_DIR) && uv build

build-frontend: ## Build frontend (Node) only
	@echo "Building frontend packages..."
	pnpm turbo build $(FRONTEND_FILTER)

test-backend: ## Run backend (Python) tests only
	@echo "Running backend tests..."
	@if [ "$$CI" = "true" ]; then \
		echo "Running in CI - excluding Redis-dependent and live API tests"; \
		cd $(BACKEND_DIR) && uv run pytest tests/ -m "not requires_redis and not live_api"; \
	else \
		echo "Excluding live API tests (run explicitly to test real provider APIs)"; \
		cd $(BACKEND_DIR) && uv run pytest tests/ -m "not live_api"; \
	fi

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

format-backend: ## Format backend (Python) code with ruff
	@echo "Formatting backend..."
	cd $(BACKEND_DIR) && uv run ruff check --fix . && uv run ruff format .

format-frontend: ## Format frontend (Node) code with ESLint
	@echo "Formatting frontend..."
	pnpm turbo run lint $(FRONTEND_FILTER) -- --fix

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
	@rm -f package-lock.json yarn.lock

docker-up: ## Start Docker services (databases, etc.)
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-clean:
	docker-compose down -v
	docker-compose rm -f
	docker-compose pull
	docker-compose build
	docker-compose up -d

docker-logs: ## Show Docker logs
	docker-compose logs -f

upgrade-db: ## Run database migrations (alembic upgrade head)
	@echo "Running database migrations..."
	cd $(BACKEND_DIR) && uv run alembic upgrade head

docs: dev-docs ## Start documentation development server (alias)

dev-docs: ## Start documentation development server
	@echo "Starting documentation development server..."
	cd apps/docs && pnpm start

build-docs: ## Build documentation for production
	@echo "Building documentation..."
	cd apps/docs && pnpm build

serve-docs: ## Serve built documentation
	@echo "Serving documentation..."
	cd apps/docs && pnpm serve

build-cli-launcher: ## Build CLI launcher (Node) only
	@echo "Building CLI launcher..."
	cd packages/cli-launcher && pnpm build

test-cli-launcher: ## Run CLI launcher (Node) tests only
	@echo "Running CLI launcher tests..."
	cd packages/cli-launcher && pnpm test

run-cli-launcher: ## Run CLI launcher (Node) only
	@echo "Running CLI launcher..."
	cd packages/cli-launcher && node dist/index.js up ../../ungitable/test-project
