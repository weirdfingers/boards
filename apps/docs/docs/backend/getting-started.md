---
sidebar_position: 1
---

# Backend Getting Started

Learn how to develop with the Boards Python backend SDK.

## Overview

The Boards backend is built with:

- **FastAPI** - Modern, fast web framework for building APIs
- **Strawberry GraphQL** - Code-first GraphQL library with Python type hints
- **SQLAlchemy 2.0** - Python SQL toolkit and ORM
- **PostgreSQL** - Relational database with JSON support
- **Redis** - In-memory cache and job queue
- **Pydantic** - Data validation using Python type annotations

## Project Structure

```
packages/backend/
├── alembic/                 # Alembic migrations (async)
│   └── versions/
├── alembic.ini
├── src/boards/
│   ├── api/                 # FastAPI application
│   ├── dbmodels/            # ORM models (authoritative)
│   ├── database/            # Connection helpers + compatibility shim
│   ├── graphql/             # GraphQL schema and resolvers
│   ├── providers/
│   ├── generators/
│   ├── storage/
│   └── config.py
└── tests/
```

## Development Workflow

### 1. Environment Setup

```bash
cd packages/backend

# Install dependencies (automatically creates venv and installs dev dependencies)
# Dev dependencies include all providers (OpenAI, Anthropic, etc.) and storage backends for typecheck
uv sync
```

### 2. Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Key configuration options:

```bash
# Database
BOARDS_DATABASE_URL=postgresql://boards:boards_dev@localhost:5433/boards_dev

# Redis
BOARDS_REDIS_URL=redis://localhost:6380/0

# Storage
BOARDS_STORAGE_PROVIDER=local
BOARDS_STORAGE_LOCAL_PATH=./uploads

# Authentication
BOARDS_AUTH_PROVIDER=supabase
BOARDS_AUTH_SUPABASE_URL=your_supabase_url
BOARDS_AUTH_SUPABASE_SERVICE_KEY=your_service_key
```

### 3. Start Development Server

```bash
# Using uvicorn directly
uvicorn boards.api.app:app --reload --port 8088

# Or using the module
python -m boards.api.app
```

The API will be available at:

- **REST API**: http://localhost:8088
- **GraphQL**: http://localhost:8088/graphql
- **Health Check**: http://localhost:8088/health

## Database Development

### Alembic-based migrations

Boards uses **Alembic** with async engines and timestamped filenames. Models live in `boards.dbmodels`.

- Create a revision (autogenerate from models):

```bash
uv run alembic revision -m "add feature" --autogenerate
```

- Apply migrations:

```bash
uv run alembic upgrade head
```

- Roll back:

```bash
uv run alembic downgrade -1
```

### Importing models

```python
# src/boards/graphql/resolvers/user.py
from boards.dbmodels import Users, Boards
```

## GraphQL API

### Type Definitions

GraphQL types are defined using Strawberry with Python type hints:

```python
# src/boards/graphql/types/user.py
import strawberry
from typing import List, Optional

@strawberry.type
class User:
    id: strawberry.ID
    email: str
    display_name: str
    avatar_url: Optional[str] = None
    boards: List["Board"] = strawberry.field(resolver=resolve_user_boards)
```

### Resolvers

```python
# src/boards/graphql/resolvers/user.py
from typing import List
from boards.dbmodels import Users, Boards

def resolve_user_boards(user: Users, info) -> List[Boards]:
    return user.boards
```

### Queries and Mutations

```python
# src/boards/graphql/queries/user.py
@strawberry.type
class UserQuery:
    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[User]:
        return get_user_by_id(id)

@strawberry.type
class UserMutation:
    @strawberry.mutation
    def update_user(self, id: strawberry.ID, input: UserInput) -> User:
        return update_user(id, input)
```

## Provider System

### Creating a Provider

```python
# src/boards/providers/my_provider.py
from boards.providers.base import BaseProvider
from typing import Dict, Any, AsyncGenerator

class MyProvider(BaseProvider):
    name = "my_provider"

    async def generate_image(
        self,
        prompt: str,
        params: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # Implementation here
        yield {"status": "processing", "progress": 50}
        yield {"status": "completed", "output": {"url": "..."}}
```

### Registering Providers

```python
# src/boards/providers/__init__.py
from .replicate import ReplicateProvider
from .my_provider import MyProvider

PROVIDERS = {
    "replicate": ReplicateProvider,
    "my_provider": MyProvider,
}
```

## Code Quality

### Pre-commit Hooks

Set up pre-commit hooks to automatically check code quality before commits:

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run all hooks manually
uv run pre-commit run --all-files

# Run a specific hook
uv run pre-commit run ruff --all-files
```

The pre-commit hooks will automatically:

- Lint and format Python code with `ruff`
- Type check with `pyright`
- Check for common issues (trailing whitespace, large files, merge conflicts)

### Linting

```bash
# Run ruff linter
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Type Checking

```bash
# Run pyright
uv run pyright

# Or use the Makefile
make typecheck-backend
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=boards --cov-report=html

# Run specific test file
uv run pytest tests/test_api.py

# Run with verbose output
uv run pytest -v
```

### Writing Tests

```python
# tests/test_providers.py
import pytest
from boards.providers.my_provider import MyProvider

@pytest.mark.asyncio
async def test_my_provider_generate_image():
    provider = MyProvider()
    async for result in provider.generate_image("test prompt", {}):
        assert "status" in result
```

## Debugging

### Logging Configuration

```python
# src/boards/config.py
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("boards")
```

### Database Debugging

```python
# Enable SQL logging
from sqlalchemy import create_engine
engine = create_engine(database_url, echo=True)  # Logs all SQL queries
```

### GraphQL Debugging

Visit http://localhost:8088/graphql to use the GraphiQL interface for testing queries and mutations.

## Next Steps

- 📊 **[Database Migrations](./migrations)** - Learn the migration workflow
- 🎨 **[Auth Providers](../auth/overview)** - Authentication system
- 📱 **[GraphQL API](./graphql-api)** - Build the API layer
- 🧪 **[Testing Guide](./testing)** - Write comprehensive tests
