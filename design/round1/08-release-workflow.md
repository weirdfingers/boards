# Release Workflow

## Monorepo
- `pnpm` or `yarn` workspaces for TS packages; Poetry for Python.
- Shared version policy: independent versions per package, with a **compatibility matrix** documented.

## CI/CD (GitHub Actions)
- Lint, typecheck (mypy/ruff, tsc), tests.
- Build & publish: PyPI (`packages/backend-sdk`), npm (`packages/frontend-hooks`, auth adapters).
- Canaries: pre-release tags (`next`) for both registries.
- Example apps use pinned ranges.

## Semantic Versioning
- Hooks are a stable API surface; breaking changes require major bumps and migration notes.
