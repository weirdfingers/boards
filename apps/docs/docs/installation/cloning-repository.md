---
sidebar_position: 2
---

# Cloning the Repository

Complete installation guide for setting up the Boards development environment from source.

## When to Use This Approach

Clone the repository when you want to:

- **Contribute** to the Boards project
- **Customize** the core toolkit deeply
- **Develop** new features or fixes
- **Learn** from the complete source code

If you just want to **use** Boards, consider [Installing Baseboards](./installing-baseboards) instead.

## Prerequisites

Before installing Boards, ensure you have the following installed:

### Required Software

- **Node.js 18+** - JavaScript runtime
  - [Download Node.js](https://nodejs.org/)
  - Verify: `node --version`

- **Python 3.12+** - Backend programming language
  - [Download Python](https://www.python.org/downloads/)
  - Verify: `python --version` or `python3 --version`

- **pnpm** - Fast, disk space efficient package manager
  - Install: `npm install -g pnpm`
  - Or via Homebrew: `brew install pnpm`
  - Or via script: `curl -fsSL https://get.pnpm.io/install.sh | sh -`
  - Verify: `pnpm --version`

- **Docker & Docker Compose** - For local database services
  - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Verify: `docker --version` and `docker compose version`

- **Git** - Version control
  - [Download Git](https://git-scm.com/downloads)
  - Verify: `git --version`

### Package Managers

#### Install pnpm

```bash
# Via npm
npm install -g pnpm

# Via Homebrew (macOS)
brew install pnpm

# Via script
curl -fsSL https://get.pnpm.io/install.sh | sh -
```

#### Install uv (Python)

```bash
# Via pip
pip install uv

# Via Homebrew (macOS)
brew install uv

# Via script
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:

```bash
uv --version
```

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/weirdfingers/boards.git
cd boards
```

### 2. Install Dependencies

The Makefile provides convenient commands for setup:

```bash
# Install all dependencies (Python and Node.js)
make install
```

This will:

- Install Python dependencies with `uv`
- Install Node.js dependencies with `pnpm`
- Set up workspace linking

**What happens under the hood:**
- Python packages in `packages/backend/` are installed in editable mode
- Node packages are linked via pnpm workspaces
- All dependencies are installed according to lock files

### 3. Start Services

Start the required database and cache services:

```bash
# Start PostgreSQL and Redis via Docker
make docker-up
```

This creates:

- **PostgreSQL 15** on port 5433
  - Database: `boards_dev`
  - User: `boards`
  - Password: `boards_dev`
- **Redis 7** on port 6380

**Verify services are running:**

```bash
docker ps | grep boards
```

You should see `boards-postgres` and `boards-redis` containers running.

### 4. Database Setup

Initialize the database schema:

```bash
cd packages/backend

# Create virtual environment and install dependencies
# Note: uv sync automatically installs dev dependencies (includes all providers/storage for typecheck)
uv sync

# Apply database migrations
uv run alembic upgrade head
```

**What this does:**
- Creates all database tables (boards, artifacts, jobs, etc.)
- Sets up indexes and constraints
- Prepares the database for development

**Verify migration:**

```bash
# Connect to database
psql -h localhost -p 5433 -U boards -d boards_dev

# List tables
\dt

# Exit
\q
```

### 5. Set Up Pre-commit Hooks (Optional but Recommended)

Pre-commit hooks automatically run linters and type checks before each commit:

```bash
# Install pre-commit hooks
cd packages/backend
uv run pre-commit install                      # Install commit hooks
uv run pre-commit install --hook-type pre-push  # Install push hooks

# Manually run all hooks (optional - they'll run automatically)
uv run pre-commit run --all-files              # Run commit hooks
uv run pre-commit run --hook-stage push --all-files  # Run push hooks (includes tests)
```

**On every commit**, the hooks automatically:

- Lint Python code with `ruff`
- Format Python code with `ruff format`
- Type check backend with `pyright`
- Lint frontend packages
- Type check frontend packages
- Check for common issues (trailing whitespace, large files, etc.)

**Before every push**, the hooks automatically:

- Run all backend tests (pytest)
- Run all frontend tests (vitest)

**Why use pre-commit hooks?**
- Catch issues before they reach CI
- Maintain consistent code quality
- Save time in code review

### 6. Start Development Servers

```bash
# Return to project root
cd ../..

# Start all development servers
make dev
```

This starts:
- **Backend API** at http://localhost:8088
- **Frontend example** at http://localhost:3033
- **Documentation** at http://localhost:4500
- **GraphQL playground** at http://localhost:8088/graphql

**Or start individually:**

```bash
# Backend only
make dev-backend
# Or: cd packages/backend && uvicorn boards.api.app:app --reload --port 8088

# Frontend only
make dev-frontend
# Or: cd apps/baseboards && pnpm dev

# Worker (for job processing)
make dev-worker
# Or: cd packages/backend && uv run python -m boards.workers.worker

# Documentation
make dev-docs
# Or: cd apps/docs && pnpm start
```

## Verify Installation

### Backend API

Check the backend is running:

```bash
curl http://localhost:8088/health
# Should return: {"status": "healthy"}
```

### GraphQL Playground

Open http://localhost:8088/graphql in your browser to access the GraphQL playground.

Try a test query:

```graphql
query {
  generators {
    name
    type
    provider
  }
}
```

### Frontend Example

Open http://localhost:3033 in your browser to see the example Next.js application (Baseboards reference implementation).

### Documentation

Open http://localhost:4500 in your browser to browse the documentation locally.

## Troubleshooting

### Common Issues

#### Docker services won't start

```bash
# Check if ports are in use
lsof -i :5433  # PostgreSQL
lsof -i :6380  # Redis

# Reset Docker containers
make docker-down
make docker-up

# View logs
make docker-logs
```

#### Python dependency issues

```bash
# Clean and reinstall
cd packages/backend
rm -rf .venv
uv sync  # Automatically includes dev dependencies

# Verify installation
uv pip list
```

#### Node.js dependency issues

```bash
# Clean and reinstall
pnpm clean
pnpm install

# If issues persist, clear cache
pnpm store prune
pnpm install
```

#### Database connection errors

```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Test connection manually
psql -h localhost -p 5433 -U boards -d boards_dev

# Check backend environment variables
cat packages/backend/.env

# Should include:
# DATABASE_URL=postgresql://boards:boards_dev@localhost:5433/boards_dev
```

#### TypeScript errors in frontend

```bash
# Regenerate types
make typecheck

# Or manually
cd packages/frontend
pnpm typecheck
```

#### Migration errors

```bash
# Check migration status
cd packages/backend
uv run alembic current

# Rollback if needed
uv run alembic downgrade -1

# Reapply
uv run alembic upgrade head
```

### Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/weirdfingers/boards/issues)
- **Discussions**: [Ask questions](https://github.com/weirdfingers/boards/discussions)
- **Documentation**: [Browse docs](https://weirdfingers.github.io/boards/)
- **Discord**: [Join community](https://discord.gg/rvVuHyuPEx)

## Development Tools

### Recommended IDE Setup

- **VS Code** with extensions:
  - Python
  - Pylance
  - ES7+ React/Redux/React-Native snippets
  - GraphQL: Language Feature Support
  - Prettier - Code formatter
  - ESLint

### Code Quality Tools

All tools are configured and can be run via Make:

```bash
# Run all linters
make lint

# Lint backend only
make lint-backend

# Lint frontend only
make lint-frontend

# Type checking
make typecheck

# Run all tests
make test

# Test backend only
make test-backend

# Test frontend only
make test-frontend

# Build all packages
make build
```

### Understanding the Monorepo

The repository uses:

- **pnpm workspaces** for Node.js packages
- **uv** for Python package management
- **Turborepo** for build orchestration
- **Make** for convenient commands

**Package structure:**

```
boards/
├── packages/
│   ├── backend/          # Python backend (published to PyPI)
│   ├── frontend/         # React hooks (published to npm as @weirdfingers/boards)
│   └── cli-launcher/     # Baseboards CLI (published to npm)
├── apps/
│   ├── baseboards/       # Reference Next.js app
│   └── docs/            # Documentation website
├── docker/              # Docker Compose configs
├── Makefile            # Convenient commands
└── turbo.json          # Turborepo configuration
```

See [CLAUDE.md](https://github.com/weirdfingers/boards/blob/main/CLAUDE.md) for detailed architecture and contribution guidelines.

## Next Steps

Now that you have the development environment set up:

- 📚 **[Backend Development](../backend/getting-started)** - Start building with the Python SDK
- ⚛️ **[Frontend Integration](../frontend/getting-started)** - Use React hooks
- 🎨 **[Creating Generators](../generators/creating-generators)** - Add new AI providers
- 🧪 **[Testing Guide](../backend/testing)** - Write and run tests
- 🤝 **[Contributing Guide](../guides/contributing)** - Contribute to the project
- 🚀 **[Deployment Guide](../deployment/overview)** - Deploy to production
