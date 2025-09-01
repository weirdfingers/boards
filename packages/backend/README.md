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

```bash
# Install with uv
cd packages/backend
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

### Run the development server

```bash
# Using uvicorn directly
uvicorn boards.api.app:app --reload --port 8000

# Or using the module
python -m boards.api.app
```

### Access the GraphQL playground

Open http://localhost:8000/graphql in your browser.

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

## License

MIT
