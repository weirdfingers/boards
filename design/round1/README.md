# Open-Source Creative Toolkit (Working Title)

A client-server toolkit for creatives to generate, manage, and collaborate on AI-generated artifacts (images, video, audio, text).

## Goals
- Pluggable AI provider support
- **Pluggable authentication** (Supabase Auth, Clerk, Auth0, custom)
- Credit-based usage tracking
- Collaborative board concept
- Extensible database schema
- First-class docs & examples
- **Frontend: hooks-first, UI-agnostic** (no required components)

## Modules
1. [System Architecture](01-system-architecture.md)
2. [Database Schema](02-database-schema.md)
3. [Background Tasks](03-background-tasks.md)
4. [Auth & Authorization](04-auth-authorization.md)
5. [Board UI](05-board-ui.md)
6. [LoRA Support](06-lora-support.md)
7. [Documentation Strategy](07-docs-strategy.md)
8. [Release Workflow](08-release-workflow.md)
9. [Roadmap](09-roadmap.md)
10. [Frontend Hooks API](10-frontend-hooks.md)

## Package Layout (proposed)
- `packages/backend` (Python, PyPI): DB models, provider adapters, job API client
- `packages/frontend` (TypeScript, npm): **React hooks** for data access, auth, generation
- `packages/provider-plugins/*` (both sides as needed)
- `apps/examples/*` (minimal UIs that consume hooks)
