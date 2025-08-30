# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Boards is an open-source creative toolkit for AI-generated content (images, video, audio, text) built as a monorepo with both Python and TypeScript/JavaScript components.

## Architecture

**Monorepo Structure:**
- `/packages/` - Shared libraries (Python backend, React frontend)
- `/apps/` - Applications (Next.js example app, Docusaurus docs)
- `/design/` - Architecture and design documents

**Tech Stack:**
- **Backend**: Python 3.12 with SQLAlchemy + Supabase (storage and optional auth)
- **Frontend**: React + Next.js with TypeScript
- **Job System**: Framework-agnostic queue (RQ or Dramatiq) with workers
- **API**: GraphQL (Ariadne) for data/relations; REST + SSE for job submission/progress
- **Infrastructure**: PostgreSQL, Redis (via Docker Compose)
- **Package Management**: pnpm (Node) and uv (Python)
- **Build System**: Turborepo for orchestrating builds

## Essential Commands

```bash
# Initial setup
make install              # Install all dependencies (Python and Node)
make docker-up           # Start PostgreSQL and Redis

# Development
make dev                 # Start all development servers
pnpm turbo dev          # Alternative: start dev servers via Turbo

# Documentation
make docs               # Start documentation development server
make docs-dev           # Start documentation development server (same as above)
make docs-build         # Build documentation for production
make docs-serve         # Serve built documentation

# Testing
make test               # Run all tests (Python pytest + Node tests)
pnpm turbo test         # Run Node tests only
uv run pytest tests/    # Run Python tests in a specific package

# Code Quality
make lint               # Run all linters (ruff, pyright for Python; ESLint for JS)
make typecheck          # Run TypeScript type checking
pnpm turbo lint         # Run Node linters only
pnpm turbo typecheck    # Run TypeScript checking only

# Building
make build              # Build all packages (Python and Node)
pnpm turbo build        # Build Node packages only

# Docker Services
make docker-up          # Start PostgreSQL and Redis
make docker-down        # Stop services
make docker-logs        # View service logs

# Cleanup
make clean              # Remove all build artifacts and dependencies
```

## Development Workflow

1. **Python packages**: Located in `/packages/*/` with `pyproject.toml` or `setup.py`. Installed in editable mode during setup using uv.
2. **Node packages**: Managed via pnpm workspaces. Internal packages referenced as `workspace:*`.
3. **Turbo pipeline**: Configured in `turbo.json` with build dependencies and caching.

## Key Design Principles

- **Hooks-first frontend design**: The toolkit ships React hooks, not mandatory UI components
- **Pluggable auth**: Support for multiple auth providers via adapters (Supabase, Clerk, Auth0, custom JWT/OIDC)
- **Observability**: Structured logs, job metrics, audit trail on credit transactions

## Database Configuration

Local development uses Docker Compose with:
- PostgreSQL 15 on port 5432 (user: boards, password: boards_dev, database: boards_dev)
- Redis 7 on port 6379