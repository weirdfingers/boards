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
│   ├── auth/                # Authentication adapters
│   ├── dbmodels/            # ORM models (authoritative)
│   ├── database/            # Connection helpers + compatibility shim
│   ├── generators/          # AI content generators
│   ├── graphql/             # GraphQL schema and resolvers
│   ├── jobs/                # Job queue integration
│   ├── progress/            # Progress tracking for long-running jobs
│   ├── storage/             # Storage backends
│   ├── workers/             # Background worker implementations
│   └── config.py
└── tests/
```

## Development Workflow

### 1. Environment Setup

```bash
cd packages/backend

# Install dependencies (automatically creates venv and installs dev dependencies)
# Dev dependencies include all generators (fal.ai, Replicate, OpenAI, etc.) and storage backends for typecheck
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

## Generator System

Generators are responsible for creating AI-generated content (images, video, audio, text). Each generator wraps a specific AI model or API and provides a consistent interface.

### Creating a Generator

```python
# src/boards/generators/implementations/my_service/image/my_generator.py
from pydantic import BaseModel, Field
from boards.generators.base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class MyGeneratorInput(BaseModel):
    """Input schema for MyGenerator."""
    prompt: str = Field(description="The text prompt for image generation")
    num_images: int = Field(default=1, ge=1, le=4, description="Number of images to generate")


class MyGenerator(BaseGenerator):
    """Custom image generator implementation."""

    name = "my-generator"
    artifact_type = "image"
    description = "My custom image generator"

    def get_input_schema(self) -> type[MyGeneratorInput]:
        return MyGeneratorInput

    async def generate(
        self, inputs: MyGeneratorInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        # Call your AI service here
        # Use context.store_image_result() to store outputs
        artifact = await context.store_image_result(
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: MyGeneratorInput) -> float:
        """Estimate cost in USD."""
        return 0.05 * inputs.num_images
```

### Registering Generators

Generators are registered via the global registry:

```python
# src/boards/generators/implementations/my_service/__init__.py
from boards.generators.registry import registry
from .image.my_generator import MyGenerator

# Register at module load time
registry.register(MyGenerator())
```

### Generator Context

The `GeneratorExecutionContext` provides utilities for:
- `resolve_artifact()` - Resolve input artifacts to local file paths
- `store_image_result()`, `store_video_result()`, `store_audio_result()`, `store_text_result()` - Store outputs
- `publish_progress()` - Send progress updates for long-running jobs
- `set_external_job_id()` - Track external API job IDs

## Code Quality

### Pre-commit Hooks

Set up pre-commit hooks to automatically check code quality before commits:

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install                      # Runs on every commit
uv run pre-commit install --hook-type pre-push  # Runs before push

# Run all hooks manually
uv run pre-commit run --all-files              # Commit hooks
uv run pre-commit run --hook-stage push --all-files  # Push hooks (includes tests)

# Run a specific hook
uv run pre-commit run ruff --all-files
```

**On every commit**, the hooks automatically:

- Lint and format Python code with `ruff`
- Type check with `pyright`
- Lint and type check frontend packages
- Check for common issues (trailing whitespace, large files, merge conflicts)

**Before every push**, the hooks automatically:

- Run all backend tests (pytest)
- Run all frontend tests (vitest)

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
# tests/generators/test_my_service.py
import pytest
from boards.generators.implementations.my_service.image.my_generator import MyGenerator, MyGeneratorInput
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_my_generator_generate():
    generator = MyGenerator()
    inputs = MyGeneratorInput(prompt="test prompt")
    context = AsyncMock()  # Mock the GeneratorExecutionContext
    result = await generator.generate(inputs, context)
    assert result.outputs is not None
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
