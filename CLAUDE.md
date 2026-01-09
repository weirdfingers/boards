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
make dev                 # Start all development servers (backend + frontend)
make dev-backend         # Start backend development server only
make dev-worker          # Start background worker (development)
make dev-worker-watch    # Start background worker with auto-reload (requires entr)
make dev-frontend        # Start frontend development servers only
pnpm turbo dev          # Alternative: start dev servers via Turbo

# Documentation
make docs               # Start documentation development server
make dev-docs           # Start documentation development server (same as above)
make build-docs         # Build documentation for production
make serve-docs         # Serve built documentation

# Testing
make test               # Run all tests (Python pytest + Node tests)
make test-backend       # Run backend (Python) tests only
make test-frontend      # Run frontend (Node) tests only
pnpm turbo test         # Run Node tests only via Turbo
uv run pytest tests/    # Run Python tests in a specific package

# Code Quality
make lint               # Run all linters (ruff, pyright for Python; ESLint for JS)
make lint-backend       # Lint backend (Python) only
make lint-frontend      # Lint frontend (Node) only
make typecheck          # Run all type checking (Python and TypeScript)
make typecheck-backend  # Typecheck backend (Python) only
make typecheck-frontend # Typecheck frontend (TypeScript) only
pnpm turbo lint         # Run Node linters only via Turbo
pnpm turbo typecheck    # Run TypeScript checking only via Turbo

# Building
make build              # Build all packages (Python and Node)
make build-backend      # Build backend (Python) only
make build-frontend     # Build frontend (Node) only
pnpm turbo build        # Build Node packages only via Turbo

# Docker Services
make docker-up          # Start PostgreSQL and Redis
make docker-down        # Stop services
make docker-logs        # View service logs

# Cleanup
make clean              # Remove all build artifacts and dependencies
make clean-backend      # Clean backend (Python) artifacts only
make clean-frontend     # Clean frontend (Node) artifacts only

# Other
make help               # Show all available Makefile commands
```

## Development Workflow

1. **Python packages**: Located in `/packages/*/` with `pyproject.toml` or `setup.py`. Installed in editable mode during setup using uv.
2. **Node packages**: Managed via pnpm workspaces. Internal packages referenced as `workspace:*`.
3. **Turbo pipeline**: Configured in `turbo.json` with build dependencies and caching.

## Key Design Principles

- **Hooks-first frontend design**: The toolkit ships React hooks, not mandatory UI components
- **Pluggable auth**: Support for multiple auth providers via adapters (Supabase, Clerk, Auth0, custom JWT/OIDC)
- **Observability**: Structured logs, job metrics, audit trail on credit transactions
- **GraphQL abstraction**: Example applications MUST NOT directly import from `urql` or GraphQL operations (e.g., `@weirdfingers/boards/graphql/operations`). All GraphQL usage must be abstracted behind hooks from `@weirdfingers/boards` (e.g., `useBoards`, `useBoard`, `useGenerators`). When adding new GraphQL functionality, create a hook in `/packages/frontend/src/hooks/` first, then use that hook in example applications.

## Code Placement Guidelines

**CRITICAL**: Boards is a toolkit of reusable packages, not just an application. Most code should go into published packages (`packages/`), not the application (`apps/baseboards`).

### Published Packages

The following packages are published to public registries:

- **`packages/backend`** → PyPI (Python package for backends)
- **`packages/frontend`** → npm as `@weirdfingers/boards` (React hooks)
- **`packages/cli-launcher`** → npm (CLI tool for scaffolding/deployment)
- **Auth packages** (planned) → npm as `@weirdfingers/boards-auth-*` (separate packages per provider)

### Package Decision Tree

**When adding new code, ask:**

1. **Is this specific to the Baseboards application UI/UX?**
   - YES → `apps/baseboards`
   - NO → Continue to question 2

2. **Is this reusable toolkit functionality?**
   - NO → Reconsider the design
   - YES → Continue to question 3

3. **Is this backend/server-side logic?**
   - YES → `packages/backend`
   - NO → Continue to question 4

4. **Is this React/frontend logic?**
   - YES → `packages/frontend`
   - NO → Determine appropriate package (CLI, auth, etc.)

### packages/backend (Python - Published to PyPI)

**SHOULD contain:**
- GraphQL schema definitions (Strawberry types and resolvers)
- SQLAlchemy models and database logic
- Business logic and service layer
- FastAPI/Starlette routes and middleware
- Auth plugins/adapters (backend auth logic)
- Job queue integration (RQ/Dramatiq workers)
- Database migrations
- Reusable utilities for backend development

**SHOULD NOT contain:**
- Application-specific business rules
- Hardcoded configuration for specific deployments
- Frontend-specific logic

**Example:**
```python
# ✅ Good - Generic board creation logic
@strawberry.mutation
def create_board(self, info: Info, input: CreateBoardInput) -> Board:
    """Create a new board - reusable across any Boards deployment"""
    board = Boards()
    board.title = input.title
    board.description = input.description
    # ... generic board creation logic
    return board

# ❌ Bad - Application-specific business rule
@strawberry.mutation
def create_board(self, info: Info, input: CreateBoardInput) -> Board:
    """Create board with hardcoded Baseboards-specific limits"""
    if user.boards_count > 10:  # Hardcoded limit specific to Baseboards app
        raise Exception("Maximum 10 boards")
    # ...
```

### packages/frontend (React/TypeScript - Published to npm)

**SHOULD contain:**
- React hooks for all Boards functionality
- GraphQL operations and fragments
- urql client configuration and exchanges
- TypeScript type definitions for GraphQL responses
- Generic, unstyled React components (sparingly - favor hooks)
- Frontend auth adapters (Supabase, Clerk integration)
- SSE/WebSocket utilities
- Reusable state management utilities

**MUST be framework-agnostic:**
- React only (no Next.js-specific code)
- Should work with Remix, Vite, Create React App, etc.
- No `next/router`, `next/navigation`, `next/image`, etc.

**Components policy:**
- Favor hooks over components
- If shipping components, they MUST support:
  - Arbitrary theming (no hardcoded styles)
  - Accessibility (a11y)
  - Internationalization (i18n)
- When in doubt, ship a hook and let apps build their own UI

**SHOULD NOT contain:**
- Next.js-specific code
- Styled/opinionated components
- Application business logic
- Direct imports that bypass hooks (apps importing from `/graphql/operations` directly)

**Example:**
```typescript
// ✅ Good - Generic hook for any React app
export function useBoards() {
  const [result] = useQuery({ query: BoardsQuery });
  return {
    boards: result.data?.boards ?? [],
    loading: result.fetching,
    error: result.error,
  };
}

// ✅ Good - Unstyled, accessible component
export function BoardCard({
  board,
  className,
  onSelect
}: BoardCardProps) {
  return (
    <article
      className={className}
      role="button"
      aria-label={board.title}
      onClick={() => onSelect?.(board)}
    >
      {/* Minimal, unstyled structure */}
    </article>
  );
}

// ❌ Bad - Next.js-specific code
import { useRouter } from 'next/navigation';
export function useBoards() {
  const router = useRouter();  // Not framework-agnostic!
  // ...
}

// ❌ Bad - Styled, opinionated component
export function BoardCard({ board }: BoardCardProps) {
  return (
    <div className="bg-blue-500 rounded-lg p-4 shadow-xl">
      {/* Hardcoded Tailwind styles - should be in app */}
    </div>
  );
}
```

### apps/baseboards (Next.js - Published via Docker)

**Purpose:** Baseboards serves dual roles:
1. **Reference implementation** - demonstrates best practices for using the packages
2. **Standalone application** - production-ready Boards instance deployable via Docker

**SHOULD contain:**
- Next.js pages, layouts, and routing
- UI components with styling (Tailwind, Radix UI, etc.)
- Application-specific configuration (environment variables, themes)
- Sensible defaults that users can deploy as-is
- Example flows demonstrating package usage
- Generic application logic (not overly opinionated)

**SHOULD import:**
- Hooks from `@weirdfingers/boards`
- Types from `@weirdfingers/boards`

**SHOULD NOT import:**
- Direct urql client usage (use hooks instead)
- GraphQL operations from `@weirdfingers/boards/graphql/operations`
- Anything that bypasses the hooks abstraction

**SHOULD NOT contain:**
- Reusable business logic (move to `packages/frontend` or `packages/backend`)
- Hardcoded business rules that make it too opinionated
- Backend logic (keep in `packages/backend`)

**Philosophy:** Baseboards should be both:
- Generic enough to deploy unchanged for most use cases
- Well-structured enough to serve as a customization starting point

**Example:**
```typescript
// ✅ Good - Uses hooks from the package
import { useBoards, useCreateBoard } from '@weirdfingers/boards';

export function BoardsPage() {
  const { boards, loading } = useBoards();
  const createBoard = useCreateBoard();

  return (
    <div className="container mx-auto">
      {/* Baseboards-specific styled UI */}
      {boards.map(board => (
        <StyledBoardCard key={board.id} board={board} />
      ))}
    </div>
  );
}

// ❌ Bad - Bypasses hooks, imports GraphQL directly
import { useQuery } from 'urql';
import { BoardsQuery } from '@weirdfingers/boards/graphql/operations';

export function BoardsPage() {
  const [result] = useQuery({ query: BoardsQuery });  // Should use useBoards() hook
  // ...
}

// ❌ Bad - Reusable logic that should be in packages/frontend
export function useBoardValidation() {
  // This is generic logic that other apps would need - move to packages/frontend!
  return { validateTitle, validateDescription };
}
```

### packages/cli-launcher (Node.js - Published to npm)

**SHOULD contain:**
- CLI commands for project scaffolding
- Docker deployment utilities
- Development environment setup

**SHOULD NOT contain:**
- Application business logic
- Backend/frontend code (import from published packages instead)

### Auth Packages (Planned - Published to npm)

**Future packages:**
- `@weirdfingers/boards-auth-supabase`
- `@weirdfingers/boards-auth-clerk`
- `@weirdfingers/boards-auth-auth0`

Each should contain frontend auth adapter implementations for their respective providers.

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
   - Search for any component usage in example applications

3. **Validation**: GraphQL queries that reference non-existent fields will fail at schema validation (before resolver execution), returning errors like "Cannot query field 'fieldName' on type 'TypeName'". This prevents resolvers from being called.

**Example workflow when removing a field**:
```bash
# 1. Remove from backend GraphQL type
# 2. Search frontend for references
grep -r "fieldName" packages/frontend apps/
# 3. Update all found references
# 4. Run typecheck to catch any missed TypeScript references
make typecheck
```

### Git Commit Policy
**IMPORTANT**: Claude Code must NEVER commit changes to git without being explicitly instructed to do so by the user.

Claude Code should:
- Make code changes as requested
- Run tests and verify changes
- Show git status and explain what files have been modified
- Suggest commit messages if helpful

But Claude Code must NOT:
- Run `git add` commands
- Run `git commit` commands
- Run `git push` commands

Unless the user explicitly asks for commits to be made.

**CRITICAL**: Claude Code must NEVER push to remote repositories. Even when explicitly instructed to commit changes, always ask the user to push manually. This prevents accidental pushes to production or shared branches.
