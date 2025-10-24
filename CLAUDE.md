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
- **API**: GraphQL (Strawberry) with urql client; SSE for job progress
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
- **GraphQL abstraction**: Example applications MUST NOT directly import from `urql` or GraphQL operations (e.g., `@weirdfingers/boards/graphql/operations`). All GraphQL usage must be abstracted behind hooks from `@weirdfingers/boards` (e.g., `useBoards`, `useBoard`, `useGenerators`). When adding new GraphQL functionality, create a hook in `/packages/frontend/src/hooks/` first, then use that hook in example apps.

## Database Configuration

Local development uses Docker Compose with:

- PostgreSQL 15 on port 5433 (user: boards, password: boards_dev, database: boards_dev)
- Redis 7 on port 6380

## Code Quality Rules

### Type Checking and Testing
- To typecheck the backend and frontend, run `make typecheck` at the root of the project
- To run tests for the backend and frontend, run `make test` at the root of the project

### Logging
- For backend logging, always use `@packages/backend/src/boards/logging.py` which is based on `structlog`
- Use keyword arguments for log data, avoid f-strings
- Never use `exc_info=True` in log statements

### SQLAlchemy Object Creation
**IMPORTANT**: When creating SQLAlchemy model instances, DO NOT pass properties as kwargs to the constructor. Instead, set properties explicitly after instantiation. This allows the type checker (pyright) to catch incorrect property names.

**Bad** (kwargs bypass type checking):
```python
new_board = Boards(
    tenant_id=tenant_uuid,
    owner_id=auth_context.user_id,
    title=input.title,
    descritpion=input.description,  # Typo won't be caught!
)
```

**Good** (explicit assignment catches typos):
```python
new_board = Boards()
new_board.tenant_id = tenant_uuid
new_board.owner_id = auth_context.user_id
new_board.title = input.title
new_board.descritpion = input.description  # Type checker will error!
```

### GraphQL Schema Changes
**CRITICAL**: When modifying GraphQL types in the backend, you MUST update the frontend in the same commit:

1. **Backend changes** in `/packages/backend/src/boards/graphql/types/`:
   - Update the Strawberry GraphQL type definition
   - If removing/renaming fields, grep the frontend codebase first

2. **Frontend changes** that MUST be synchronized:
   - Update GraphQL fragments in `/packages/frontend/src/graphql/operations.ts`
   - Update TypeScript interfaces in `/packages/frontend/src/hooks/`
   - Search for any component usage in `/apps/example-nextjs/`

3. **Validation**: GraphQL queries that reference non-existent fields will fail at schema validation (before resolver execution), returning errors like "Cannot query field 'fieldName' on type 'TypeName'". This prevents resolvers from being called.

**Example workflow when removing a field**:
```bash
# 1. Remove from backend GraphQL type
# 2. Search frontend for references
grep -r "fieldName" packages/frontend apps/example-nextjs
# 3. Update all found references
# 4. Run typecheck to catch any missed TypeScript references
make typecheck
```