---
sidebar_position: 2
---

# Makefile Commands Reference

Complete reference for all Makefile commands available in the Boards monorepo.

## Quick Reference

```bash
make help    # Show all available commands with descriptions
```

## Installation & Setup

### `make install`

Install all dependencies (Python and Node.js packages).

```bash
make install
```

Equivalent to running both `make install-backend` and `make install-frontend`.

### `make install-backend`

Install only Python backend dependencies using `uv`.

```bash
make install-backend
```

### `make install-frontend`

Install only Node.js frontend dependencies using `pnpm`.

```bash
make install-frontend
```

## Development Servers

### `make dev`

Start all development servers in parallel:
- Backend API at http://localhost:8088
- Frontend example at http://localhost:3033

```bash
make dev
```

### `make dev-backend`

Start only the backend development server with auto-reload.

```bash
make dev-backend
```

### `make dev-frontend`

Start only frontend development servers (all frontend packages).

```bash
make dev-frontend
```

### `make dev-worker`

Start the background worker for processing generation jobs.

```bash
make dev-worker
```

### `make dev-worker-watch`

Start the background worker with auto-reload on file changes (requires `entr`).

```bash
# Install entr first: brew install entr
make dev-worker-watch
```

## Code Quality

### `make format`

**NEW** - Format all code (both Python and Node.js). Runs auto-fixers for linting and formatting issues.

```bash
make format
```

This runs:
- `ruff check --fix` and `ruff format` on Python code
- ESLint with `--fix` on TypeScript/JavaScript code

**Recommended:** Run this before committing to avoid pre-commit hook failures.

### `make format-backend`

Format only Python backend code with ruff.

```bash
make format-backend
```

### `make format-frontend`

Format only frontend Node.js code with ESLint.

```bash
make format-frontend
```

### `make lint`

Run all linters (both Python and Node.js).

```bash
make lint
```

### `make lint-backend`

Run ruff linter and pyright type checker on Python code.

```bash
make lint-backend
```

### `make lint-frontend`

Run ESLint on all frontend packages.

```bash
make lint-frontend
```

### `make typecheck`

Run type checking for all packages (Python and TypeScript).

```bash
make typecheck
```

### `make typecheck-backend`

Run pyright type checker on Python code.

```bash
make typecheck-backend
```

### `make typecheck-frontend`

Run TypeScript type checker on frontend packages.

```bash
make typecheck-frontend
```

## Testing

### `make test`

Run all tests (both Python and Node.js).

```bash
make test
```

### `make test-backend`

Run Python backend tests with pytest. Excludes live API tests by default.

```bash
make test-backend
```

In CI environments, also excludes Redis-dependent tests.

### `make test-frontend`

Run frontend tests with vitest.

```bash
make test-frontend
```

## Building

### `make build`

Build all packages (both Python and Node.js).

```bash
make build
```

### `make build-backend`

Build only the Python backend package.

```bash
make build-backend
```

### `make build-frontend`

Build only frontend Node.js packages using Turborepo.

```bash
make build-frontend
```

### `make build-cli-launcher`

Build the CLI launcher package.

```bash
make build-cli-launcher
```

## Documentation

### `make docs` or `make dev-docs`

Start the documentation development server at http://localhost:4500.

```bash
make docs
```

### `make build-docs`

Build documentation for production.

```bash
make build-docs
```

### `make serve-docs`

Serve built documentation locally.

```bash
make serve-docs
```

## Docker Services

### `make docker-up`

Start Docker services (PostgreSQL and Redis).

```bash
make docker-up
```

### `make docker-down`

Stop Docker services.

```bash
make docker-down
```

### `make docker-logs`

View logs from Docker services.

```bash
make docker-logs
```

### `make docker-clean`

Clean and restart Docker services with fresh containers.

```bash
make docker-clean
```

## Database

### `make upgrade-db`

Run database migrations (Alembic upgrade head).

```bash
make upgrade-db
```

For more database operations, see the [Database Migrations](../backend/migrations) guide.

## Cleanup

### `make clean`

Clean all build artifacts and caches (both Python and Node.js).

```bash
make clean
```

### `make clean-backend`

Clean only Python backend artifacts:
- `__pycache__` directories
- `.egg-info` directories
- `dist` and `build` directories
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`

```bash
make clean-backend
```

### `make clean-frontend`

Clean only frontend Node.js artifacts:
- `node_modules` directories
- `.next` directories
- `.turbo` cache

```bash
make clean-frontend
```

## Common Workflows

### Starting Fresh Development

```bash
make install          # Install dependencies
make docker-up        # Start PostgreSQL and Redis
make upgrade-db       # Run database migrations
make dev              # Start all dev servers
```

### Pre-commit Checks

```bash
make format           # Format code (auto-fix issues)
make test             # Run all tests
make lint             # Check for remaining issues
make typecheck        # Verify types
```

### Building for Production

```bash
make clean            # Clean old artifacts
make build            # Build all packages
make test             # Verify everything works
```

## Tips

- **Use `make help`** to see all available commands with descriptions
- **Run `make format`** before committing to avoid pre-commit hook failures
- **Use parallel commands** like `make dev` instead of running servers separately
- **Check Docker services** with `make docker-logs` if you encounter connection issues
