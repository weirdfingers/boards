# Backend Architecture

The Boards backend is built with Python using modern async patterns and a pluggable architecture for storage, authentication, and content generation.

## Tech Stack

- **GraphQL**: Strawberry (type-hint based, async support)
- **ORM**: SQLAlchemy 2.0 with async support
- **Server**: FastAPI for REST endpoints + Strawberry GraphQL
- **Job Queue**: Dramatiq with Redis backend
- **Storage**: Pluggable system (Supabase, S3, local)

## Core Components

### [Storage System](./storage)

Pluggable storage architecture supporting multiple backends:

- Local filesystem for development
- Supabase Storage with auth integration
- S3 for enterprise deployments
- Custom providers via plugin system

### Generator System

Extensible system for AI content generation:

- **Generators**: Specific models
- **Plugin Discovery**: Automatic registration system

### Job System

Async job processing with progress tracking:

- Dramatiq task queue with Redis
- Real-time progress via Server-Sent Events
- Retry logic and error handling

### Authentication

Pluggable auth system supporting:

- Supabase Auth
- Clerk
- Custom JWT/OIDC providers
- Development mode (no auth)

## Project Structure

```
packages/backend/src/boards/
├── config.py              # Configuration management
├── database/
│   ├── models.py          # SQLAlchemy models
│   ├── connection.py      # Database connection
│   └── migrations.py      # Migration runner
├── graphql/
│   ├── schema.py          # Strawberry schema
│   ├── types/             # GraphQL types
│   ├── mutations/         # GraphQL mutations
│   └── queries/           # GraphQL queries
├── storage/
│   ├── base.py            # Storage interfaces
│   ├── config.py          # Configuration
│   ├── factory.py         # Provider factory
│   └── implementations/   # Provider implementations
├── providers/
│   ├── base.py            # Provider interfaces
│   ├── registry.py        # Provider discovery
│   └── builtin/           # Built-in providers
├── generators/
│   ├── base.py            # Generator interfaces
│   ├── registry.py        # Generator discovery
│   └── schemas.py         # Pydantic schemas
├── auth/
│   ├── base.py            # Auth interfaces
│   └── providers/         # Auth implementations
├── jobs/
│   ├── tasks.py           # Dramatiq tasks
│   └── progress.py        # Progress tracking
└── api/
    ├── app.py             # FastAPI app
    └── endpoints/         # REST endpoints
```

## Development Setup

1. **Install dependencies**:

   ```bash
   make install
   ```

2. **Start services**:

   ```bash
   make docker-up  # PostgreSQL + Redis
   make dev        # Backend + frontend
   ```

3. **Run tests**:
   ```bash
   make test
   ```

## Configuration

The backend uses environment variables and YAML files for configuration:

```bash
# Database
DATABASE_URL=postgresql://boards:boards_dev@localhost:5433/boards_dev

# Redis
REDIS_URL=redis://localhost:6380

# Storage (see Storage documentation)
BOARDS_STORAGE_DEFAULT_PROVIDER=local

# Auth
BOARDS_AUTH_PROVIDER=none  # none, supabase, clerk, jwt
```

## Key Design Principles

1. **Async First**: All I/O operations use async/await
2. **Type Safety**: Extensive use of type hints and validation
3. **Plugin Architecture**: Extensible via provider system
4. **Configuration**: Environment-aware with sensible defaults
5. **Observability**: Structured logging and metrics
6. **Security**: Input validation and access control throughout
