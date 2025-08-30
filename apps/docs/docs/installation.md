---
sidebar_position: 2
---

# Installation

Complete installation guide for setting up Boards in your development environment.

## Prerequisites

Before installing Boards, ensure you have the following installed:

### Required Software

- **Node.js 18+** - JavaScript runtime
- **Python 3.12+** - Backend programming language
- **pnpm** - Fast, disk space efficient package manager
- **Docker & Docker Compose** - For local database services
- **Git** - Version control

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

### 3. Start Services

Start the required database and cache services:

```bash
# Start PostgreSQL and Redis via Docker
make docker-up
```

This creates:
- **PostgreSQL 15** on port 5432
  - Database: `boards_dev`
  - User: `boards`
  - Password: `boards_dev`
- **Redis 7** on port 6379

### 4. Database Setup

Initialize the database schema:

```bash
cd packages/backend

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Apply initial schema
psql boards_dev < migrations/schemas/001_initial_schema.sql

# Generate SQLAlchemy models
python scripts/generate_models.py
```

### 5. Start Development Servers

```bash
# Start all development servers
make dev

# Or start individually:
# Backend only:
cd packages/backend && uvicorn boards.api.app:app --reload --port 8000

# Frontend only:
cd apps/example-nextjs && pnpm dev
```

## Verify Installation

### Backend API

Check the backend is running:

```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

### GraphQL Playground

Open http://localhost:8000/graphql in your browser to access the GraphQL playground.

### Frontend Example

Open http://localhost:3000 in your browser to see the example Next.js application.

## Troubleshooting

### Common Issues

**Docker services won't start:**
```bash
# Check if ports are in use
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Reset Docker containers
make docker-down
make docker-up
```

**Python dependency issues:**
```bash
# Clean and reinstall
cd packages/backend
rm -rf .venv
uv venv
uv pip install -e ".[dev]"
```

**Node.js dependency issues:**
```bash
# Clean and reinstall
pnpm clean
pnpm install
```

**Database connection errors:**
```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Test connection manually
psql -h localhost -U boards -d boards_dev
```

### Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/weirdfingers/boards/issues)
- **Discussions**: [Ask questions](https://github.com/weirdfingers/boards/discussions)
- **Documentation**: [Browse docs](https://weirdfingers.github.io/boards/)

## Development Tools

### Recommended IDE Setup

- **VS Code** with extensions:
  - Python
  - Pylance  
  - ES7+ React/Redux/React-Native snippets
  - GraphQL

### Code Quality Tools

All tools are configured and can be run via Make:

```bash
make lint      # Run all linters
make typecheck # TypeScript type checking
make test      # Run all tests
make build     # Build all packages
```

## Next Steps

- 📚 **[Backend Development](./backend/getting-started)** - Start building with the Python SDK
- ⚛️ **[Frontend Integration](./frontend/getting-started)** - Use React hooks
- 🚀 **[Deployment Guide](./deployment/overview)** - Deploy to production