# Backend Architecture with Strawberry GraphQL

## Overview
Python backend using Strawberry GraphQL, SQLAlchemy, and a plugin-based provider/generator system.

## Tech Stack
- **GraphQL**: Strawberry (type-hint based, async support)
- **ORM**: SQLAlchemy 2.0 with async support
- **Server**: FastAPI (REST endpoints) + Strawberry GraphQL
- **Job Queue**: Dramatiq with Redis backend
- **Storage**: Pluggable (Supabase, S3, GCS, local)
- **Client Libraries**: Apollo Client or urql for React

## Project Structure

```
packages/backend-sdk/
├── src/
│   └── boards/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── database/
│       │   ├── __init__.py
│       │   ├── models.py          # Generated SQLAlchemy models
│       │   ├── connection.py      # Database connection management
│       │   └── migrations.py      # Migration runner
│       ├── graphql/
│       │   ├── __init__.py
│       │   ├── schema.py          # Strawberry schema definition
│       │   ├── types/             # GraphQL types
│       │   │   ├── board.py
│       │   │   ├── generation.py
│       │   │   └── user.py
│       │   ├── mutations/         # GraphQL mutations
│       │   │   ├── board.py
│       │   │   └── generation.py
│       │   └── queries/           # GraphQL queries
│       │       ├── board.py
│       │       └── generation.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py            # BaseProvider abstract class
│       │   ├── registry.py        # Provider discovery/registration
│       │   └── builtin/           # Built-in providers
│       │       ├── replicate.py
│       │       ├── fal.py
│       │       └── openai.py
│       ├── generators/
│       │   ├── __init__.py
│       │   ├── base.py            # BaseGenerator abstract class
│       │   ├── registry.py        # Generator discovery/registration
│       │   └── schemas.py         # Pydantic schemas for inputs/outputs
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── base.py            # BaseStorage abstract class
│       │   └── implementations/
│       │       ├── supabase.py
│       │       ├── s3.py
│       │       └── local.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── base.py            # BaseAuth abstract class
│       │   └── providers/
│       │       ├── supabase.py
│       │       ├── clerk.py
│       │       └── jwt.py
│       ├── jobs/
│       │   ├── __init__.py
│       │   ├── tasks.py           # Dramatiq tasks
│       │   └── progress.py        # Job progress tracking
│       └── api/
│           ├── __init__.py
│           ├── app.py             # FastAPI app setup
│           └── endpoints/         # REST endpoints (SSE, webhooks)
│               ├── sse.py         # Server-sent events for progress
│               └── webhooks.py    # Provider webhooks
├── tests/
├── migrations/
│   ├── 001_initial_schema.sql
│   └── migration_runner.py
├── scripts/
│   ├── generate_models.py        # SQL → SQLAlchemy
│   └── generate_types.py         # Pydantic → TypeScript
└── pyproject.toml
```

## Strawberry GraphQL Schema

```python
# src/boards/graphql/schema.py
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional
import datetime

@strawberry.type
class User:
    id: strawberry.ID
    email: str
    display_name: str
    created_at: datetime.datetime

@strawberry.type
class Board:
    id: strawberry.ID
    title: str
    description: Optional[str]
    owner: User
    is_public: bool
    created_at: datetime.datetime
    
    @strawberry.field
    async def generations(self) -> List["Generation"]:
        # Fetch generations for this board
        pass
    
    @strawberry.field
    async def members(self) -> List["BoardMember"]:
        # Fetch board members
        pass

@strawberry.type
class Generation:
    id: strawberry.ID
    board: Board
    user: User
    generator_name: str
    provider_name: str
    artifact_type: str
    storage_url: Optional[str]
    status: str
    progress: float
    input_params: strawberry.scalars.JSON
    created_at: datetime.datetime

@strawberry.type
class Query:
    @strawberry.field
    async def board(self, id: strawberry.ID) -> Optional[Board]:
        # Fetch board by ID with permission check
        pass
    
    @strawberry.field
    async def my_boards(self) -> List[Board]:
        # Fetch boards for current user
        pass
    
    @strawberry.field
    async def generation(self, id: strawberry.ID) -> Optional[Generation]:
        # Fetch generation by ID
        pass

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_board(self, title: str, description: Optional[str] = None) -> Board:
        # Create new board
        pass
    
    @strawberry.mutation
    async def create_generation(
        self,
        board_id: strawberry.ID,
        generator_name: str,
        input_params: strawberry.scalars.JSON
    ) -> Generation:
        # Start new generation job
        pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

## Provider/Generator Plugin System

```python
# src/boards/providers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class ProviderConfig(BaseModel):
    api_key: str
    endpoint: Optional[str] = None
    additional_config: Dict[str, Any] = {}

class BaseProvider(ABC):
    """Base class for all providers"""
    
    name: str
    supported_generators: List[str]
    
    def __init__(self, config: ProviderConfig):
        self.config = config
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate provider credentials"""
        pass
    
    @abstractmethod
    def get_generator(self, name: str) -> "BaseGenerator":
        """Get a specific generator from this provider"""
        pass

# src/boards/generators/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class GenerationInput(BaseModel):
    """Base class for generation inputs"""
    pass

class GenerationOutput(BaseModel):
    """Base class for generation outputs"""
    storage_url: str
    metadata: Dict[str, Any]

class BaseGenerator(ABC):
    """Base class for all generators"""
    
    name: str
    artifact_type: str  # 'image', 'video', 'audio', etc.
    
    @abstractmethod
    def get_input_schema(self) -> type[GenerationInput]:
        """Return Pydantic schema for inputs"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        inputs: GenerationInput,
        progress_callback: Optional[callable] = None
    ) -> GenerationOutput:
        """Execute generation"""
        pass
    
    @abstractmethod
    async def estimate_cost(self, inputs: GenerationInput) -> float:
        """Estimate cost in credits"""
        pass
```

## FastAPI Integration

```python
# src/boards/api/app.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from .graphql.schema import schema

app = FastAPI(title="Boards API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL endpoint
graphql_app = GraphQLRouter(
    schema,
    path="/graphql",
    graphiql=True  # Enable GraphiQL IDE in development
)

app.include_router(graphql_app, prefix="/graphql")

# REST endpoints for SSE and webhooks
from .endpoints import sse, webhooks
app.include_router(sse.router, prefix="/api/sse")
app.include_router(webhooks.router, prefix="/api/webhooks")
```

## Configuration Management

```python
# src/boards/config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://boards:boards_dev@localhost/boards_dev"
    
    # Redis (for job queue)
    redis_url: str = "redis://localhost:6379"
    
    # Storage
    storage_provider: str = "local"  # 'local', 'supabase', 's3', 'gcs'
    storage_config: dict = {}
    
    # Auth
    auth_provider: str = "none"  # 'none', 'supabase', 'clerk', 'jwt'
    auth_config: dict = {}
    
    # Providers (loaded from YAML)
    providers_config_path: str = "providers.yaml"
    
    class Config:
        env_file = ".env"
        env_prefix = "BOARDS_"

settings = Settings()
```

## Client-Side GraphQL (React)

```typescript
// packages/frontend-hooks/src/graphql/client.ts
import { ApolloClient, InMemoryCache, createHttpLink } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';

const httpLink = createHttpLink({
  uri: process.env.NEXT_PUBLIC_GRAPHQL_URL || 'http://localhost:8000/graphql',
});

const authLink = setContext((_, { headers }) => {
  const token = localStorage.getItem('auth_token');
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
    }
  }
});

export const apolloClient = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache()
});
```

## Key Features

1. **Type Safety**: Strawberry uses Python type hints, ensuring GraphQL schema matches Python types
2. **Async First**: All database operations and API calls are async
3. **Plugin Discovery**: Providers and generators discovered via entry points or explicit registration
4. **Job Queue**: Long-running generations handled via Dramatiq tasks
5. **Progress Tracking**: SSE for real-time progress updates
6. **Multi-tenant**: All queries filtered by tenant_id from auth context