# Boards Backend SDK

Backend SDK for the Boards open-source creative toolkit for AI-generated content.

## Features

- 🎨 Multi-provider support (Replicate, Fal.ai, OpenAI, etc.)
- 🔌 Pluggable architecture for generators and providers
- 📊 GraphQL API with Strawberry
- 🗄️ PostgreSQL with SQLAlchemy 2.0
- 🔄 Migration system with SQL DDL as source of truth
- 👥 Multi-tenant support with tenant isolation
- 🔐 Pluggable authentication (Supabase, Clerk, Auth0, JWT)
- 📦 Flexible storage backends (Local, S3, GCS, Supabase)

## Installation

```bash
# Install with uv
cd packages/backend-sdk
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

Key configuration options:
- `BOARDS_DATABASE_URL`: PostgreSQL connection string
- `BOARDS_REDIS_URL`: Redis connection for job queue
- `BOARDS_STORAGE_PROVIDER`: Storage backend (local, s3, gcs, supabase)
- `BOARDS_AUTH_PROVIDER`: Authentication provider

## Database Setup

### 1. Create the database

```bash
createdb boards_dev
```

### 2. Run initial migration

```bash
# Apply the initial schema
psql boards_dev < migrations/schemas/001_initial_schema.sql
```

### 3. Generate SQLAlchemy models

```bash
python scripts/generate_models.py
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

When you need to change the database schema, follow our DDL-first migration workflow.

**Quick reference:**
```bash
# 1. Edit schema files
vim migrations/schemas/002_add_feature.sql

# 2. Generate migration scripts  
python scripts/generate_migration.py --name add_feature

# 3. Apply migration
psql boards_dev < migrations/generated/*_add_feature_up.sql

# 4. Regenerate models
python scripts/generate_models.py
```

📖 **For detailed migration workflow, see [docs/MIGRATIONS.md](docs/MIGRATIONS.md)**

## Project Structure

```
packages/backend-sdk/
├── migrations/
│   ├── schemas/          # SQL DDL source files
│   ├── generated/        # Generated migration scripts
│   └── migration_runner.py
├── scripts/
│   ├── generate_models.py    # SQL → SQLAlchemy models
│   └── generate_migration.py # Schema diff → migrations
├── src/boards/
│   ├── api/              # FastAPI application
│   ├── database/         # Database models and connection
│   ├── graphql/          # GraphQL schema and resolvers
│   ├── providers/        # Provider implementations
│   ├── generators/       # Generator implementations
│   ├── storage/          # Storage backends
│   └── config.py         # Configuration management
└── tests/
```

## License

MIT