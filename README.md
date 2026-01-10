# Boards

🎨 Open-source creative toolkit for AI-generated content (images, video, audio, text).

**[📚 Documentation](https://boards-docs.weirdfingers.com)** | **[💬 Discord](https://discord.gg/rvVuHyuPEx)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-docusaurus-blue)](https://boards-docs.weirdfingers.com)

## Overview

Boards provides a **collaborative workspace** for organizing AI-generated content into visual collections. Built with a hooks-first philosophy, it offers maximum flexibility while maintaining a powerful backend infrastructure.

### Key Features

- 🎨 **Multi-modal Generation** - Images, video, audio, and text through unified interface
- 🔌 **Pluggable Providers** - Integrate with Replicate, Fal.ai, OpenAI, and more
- 📱 **Responsive Interface** - Drag-and-drop organization with real-time updates
- 👥 **Multi-tenant Architecture** - Built for collaboration with tenant isolation
- 🗄️ **Flexible Storage** - Support for local, S3, GCS, and Supabase storage
- 🔐 **Pluggable Auth** - Integrate with Supabase, Clerk, Auth0, or custom JWT

## Quick Start

### Prerequisites

- **Node.js** 18+
- **Python** 3.12+
- **pnpm** 9+
- **Docker** and Docker Compose (for local services)
- **uv** (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/weirdfingers/boards.git
cd boards

# Install all dependencies
make install

# Start local services (PostgreSQL, Redis)
make docker-up

# Initialize database
cd packages/backend
uv run alembic upgrade head
cd ../..

# Start development servers
make dev
```

This will start:

- 🚀 **Backend API** at http://localhost:8088
- 💻 **Frontend Example** at http://localhost:3033
- 📚 **Documentation** at http://localhost:4500
- 🔧 **GraphQL Playground** at http://localhost:8088/graphql

## Project Structure

```
boards/
├── packages/
│   ├── backend/              # Python backend
│   │   ├── alembic/          # Alembic migrations (async)
│   │   ├── src/boards/       # Core backend implementation (includes dbmodels)
│   │   └── tests/            # Backend tests
│   └── frontend/             # React hooks library (@weirdfingers/boards)
├── apps/
│   └── docs/                 # Docusaurus documentation site
├── design/                   # Architecture and design documents
└── docker-compose.yml        # Local development services
```

## Tech Stack

### Backend

- **Python 3.12** with type hints
- **FastAPI** for high-performance APIs
- **Strawberry GraphQL** with code-first schema
- **SQLAlchemy 2.0** models in `boards.dbmodels`
- **Alembic** for database migrations (async, timestamped filenames)
- **PostgreSQL** with multi-tenant architecture
- **Redis** for job queue, progress tracking, and caching (required)

### Frontend

- **React 18+** with hooks-first design
- **TypeScript** for type safety
- **Next.js** compatible (App Router & Pages Router)
- **Real-time updates** via Server-Sent Events
- **Optimistic updates** for better UX

### Infrastructure

- **Docker Compose** for local development
- **pnpm workspaces** for monorepo management
- **Turborepo** for build orchestration
- **GitHub Actions** for CI/CD

## Development

### Essential Commands

```bash
# Development
make dev                # Start all development servers
make docs               # Start documentation at http://localhost:4500

# Code Quality
make format             # Format code (auto-fix issues) - run before committing
make test               # Run all tests
make lint               # Run linters
make typecheck          # Type checking

# Database Migrations
cd packages/backend
uv run alembic revision -m "your_migration" --autogenerate
uv run alembic upgrade head

# Building
make build              # Build all packages
make docs-build         # Build documentation

# Docker Services
make docker-up          # Start PostgreSQL and Redis
make docker-down        # Stop services
make docker-logs        # View service logs
```

### Database Migrations

Boards uses **Alembic** with async engines and timestamped filenames. Revisions are autogenerable from models in `src/boards/dbmodels` and support reversible `downgrade()` functions and data migrations.

## Documentation

Comprehensive documentation is available at http://localhost:4500 when running `make docs`.

### Documentation Sections

- **[Getting Started](http://localhost:4500/docs/intro)** - Project introduction
- **[Installation](http://localhost:4500/docs/installation)** - Detailed setup guide
- **[Backend Development](http://localhost:4500/docs/backend/getting-started)** - Python SDK guide
- **[Frontend Development](http://localhost:4500/docs/frontend/getting-started)** - React hooks guide
- **[Database Migrations](http://localhost:4500/docs/backend/migrations)** - Migration workflow
- **[Deployment](http://localhost:4500/docs/deployment/overview)** - Production deployment

## Contributing

We welcome contributions! Please see our [Contributing Guide](http://localhost:4500/docs/guides/contributing) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

### Code Standards

- **Python**: PEP 8 via `ruff`, type hints required
- **TypeScript**: ESLint + Prettier, strict mode
- **Commits**: Follow [Conventional Commits](https://conventionalcommits.org/)
- **Pre-commit Hooks**: Automatic linting and type checking (see [Installation Guide](http://localhost:4500/docs/installation))

## Community

- **GitHub Issues**: [Report bugs](https://github.com/weirdfingers/boards/issues)
- **Discussions**: [Ask questions](https://github.com/weirdfingers/boards/discussions)
- **Documentation**: [Browse docs](https://weirdfingers.github.io/boards/)

## License

MIT - See [LICENSE](LICENSE) file for details.
