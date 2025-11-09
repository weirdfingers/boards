# Boards Backend

Backend for the Boards open-source creative toolkit for AI-generated content.

## Features

- 🎨 Multi-provider support (Replicate, Fal.ai, OpenAI, etc.)
- 🔌 Pluggable architecture for generators and providers
- 📊 GraphQL API with Strawberry
- 🗄️ PostgreSQL with SQLAlchemy 2.0
- 🔄 Migrations with Alembic (async) and timestamped filenames
- 👥 Multi-tenant support with tenant isolation
- 🔐 Pluggable authentication (Supabase, Clerk, Auth0, JWT)
- 📦 Flexible storage backends (Local, S3, GCS, Supabase)

## Installation

### Minimal Install

The minimal installation includes core functionality with local filesystem storage only:

```bash
pip install weirdfingers-boards
```

### Install with Specific Generators

Install only the generator providers you need:

```bash
# OpenAI generators (DALL-E 3, Whisper)
pip install weirdfingers-boards[generators-openai]

# Replicate generators (Flux Pro, Lipsync)
pip install weirdfingers-boards[generators-replicate]

# fal.ai generators (nano-banana)
pip install weirdfingers-boards[generators-fal]

# Multiple generators
pip install weirdfingers-boards[generators-openai,generators-replicate]

# All generators
pip install weirdfingers-boards[generators-all]
```

### Install with Storage Backends

Add cloud storage providers as needed:

```bash
# S3 storage (AWS, MinIO, DigitalOcean Spaces)
pip install weirdfingers-boards[storage-s3]

# Supabase storage
pip install weirdfingers-boards[storage-supabase]

# Google Cloud Storage
pip install weirdfingers-boards[storage-gcs]

# All storage backends
pip install weirdfingers-boards[storage-all]
```

### Full Installation

Install everything (all generators and storage backends):

```bash
pip install weirdfingers-boards[all]
```

### Development Installation

For local development with all providers for type checking and testing:

```bash
# Clone the repository
git clone https://github.com/weirdfingers/boards.git
cd boards/packages/backend

# Install with dev dependencies (includes all providers)
uv sync
```

## Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

Key configuration options:

- `BOARDS_DATABASE_URL`: PostgreSQL connection string (e.g. postgresql://user:pass@localhost:5433/db)
- `BOARDS_REDIS_URL`: Redis connection for job queue
- `BOARDS_STORAGE_PROVIDER`: Storage backend (local, s3, gcs, supabase)
- `BOARDS_AUTH_PROVIDER`: Authentication provider

## Database Setup

### 1. Create the database

```bash
createdb boards_dev
```

### 2. Apply initial schema via Alembic

```bash
# Use Alembic to create all tables
uv run alembic upgrade head
```

## Development

### Quick Start

```bash
# Start the API server (after installation and configuration)
boards-server

# Run database migrations
boards-migrate upgrade head

# Start background workers
boards-worker
```

### Development Server

```bash
# Using uvicorn directly
uvicorn boards.api.app:app --reload --port 8088

# Or using the module
python -m boards.api.app
```

### Access the GraphQL playground

Open http://localhost:8088/graphql in your browser.

### Database migrations

When you need to change the database schema, use Alembic.

```bash
# Create a new migration (autogenerate from models in boards.dbmodels)
uv run alembic revision -m "add feature" --autogenerate

# Apply latest migrations
uv run alembic upgrade head

# Roll back one revision
uv run alembic downgrade -1
```

📖 For detailed migration workflow, see docs and examples under `apps/docs`.

## Project Structure

```
packages/backend/
├── alembic/                 # Alembic migration scripts
│   └── versions/            # Timestamped revision files
├── alembic.ini              # Alembic config
├── src/boards/
│   ├── api/                 # FastAPI application
│   ├── dbmodels/            # SQLAlchemy ORM models (authoritative)
│   ├── database/            # Connection helpers and compatibility shim
│   ├── graphql/             # GraphQL schema and resolvers
│   ├── providers/           # Provider implementations
│   ├── generators/          # Generator implementations
│   ├── storage/             # Storage backends
│   └── config.py            # Configuration management
└── tests/
```

## Community & Social

Join the Weirdfingers community:

- **TikTok**: [https://www.tiktok.com/@weirdfingers](https://www.tiktok.com/@weirdfingers)
- **X (Twitter)**: [https://x.com/_Weirdfingers_](https://x.com/_Weirdfingers_)
- **YouTube**: [https://www.youtube.com/@Weirdfingers](https://www.youtube.com/@Weirdfingers)
- **Discord**: [https://discord.gg/rvVuHyuPEx](https://discord.gg/rvVuHyuPEx)
- **Instagram**: [https://www.instagram.com/_weirdfingers_/](https://www.instagram.com/_weirdfingers_/)
## Testing

Boards uses pytest for testing with both unit tests (mocked) and optional live API tests.

### Running Tests

```bash
# Run all unit tests (excludes live API tests)
make test-backend

# Or using pytest directly
cd packages/backend
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=src/boards --cov-report=html

# Run specific test file
uv run pytest tests/generators/implementations/test_flux_pro.py -v
```

### Unit Tests vs Live API Tests

**Unit tests** (default):
- Use mocked provider SDKs
- Fast and free
- Run automatically in CI/CD
- Located: `tests/**/test_*.py`

**Live API tests** (opt-in only):
- Make real API calls to providers
- Consume API credits
- **Never run by default**
- Located: `tests/**/test_*_live.py`

### Running Live API Tests

Live tests verify real connectivity with provider APIs but cost money. They are **excluded from default test runs**.

```bash
# Set up API key
export BOARDS_GENERATOR_API_KEYS='{"REPLICATE_API_TOKEN": "r8_..."}'

# Run a specific generator's live test
uv run pytest tests/generators/implementations/test_flux_pro_live.py -v -m live_api

# Run all live tests for one provider
uv run pytest -m live_replicate -v

# Run all live tests (not recommended - expensive!)
uv run pytest -m live_api -v
```

For detailed information on live API testing, see:
- [Live API Testing Guide](docs/TESTING_LIVE_APIS.md)
- [Generator Testing Documentation](../../apps/docs/docs/generators/testing.md)

### Test Organization

```
tests/
├── conftest.py                              # Shared fixtures (database, etc.)
├── generators/
│   └── implementations/
│       ├── conftest.py                      # Generator-specific fixtures
│       ├── test_flux_pro.py                 # Unit tests (mocked)
│       ├── test_flux_pro_live.py           # Live API tests (opt-in)
│       └── ...
├── graphql/                                 # GraphQL API tests
└── storage/                                 # Storage backend tests
```

## License

MIT
