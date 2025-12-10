---
title: GraphQL API Overview
description: Overview of the Boards GraphQL API, including schema, types, queries, and mutations.
sidebar_position: 3
---

# GraphQL API

The Boards backend exposes a GraphQL API built with [Strawberry](https://strawberry.rocks/), a modern Python GraphQL library that leverages type hints for schema definition. The API provides full CRUD operations for boards, generations, and users, with real-time capabilities via Server-Sent Events.

## Endpoint

The GraphQL endpoint is available at:

```
POST /graphql
```

In development, GraphiQL (an interactive GraphQL IDE) is enabled at the same endpoint for browser-based exploration.

## Documentation Structure

The GraphQL API documentation is organized to mirror the implementation structure:

| Section | Description |
|---------|-------------|
| [Types](./graphql-api/types) | GraphQL type definitions (Board, Generation, User, etc.) |
| [Queries](./graphql-api/queries) | Available read operations |
| [Mutations](./graphql-api/mutations) | Available write operations |
| [Access Control](./graphql-api/access-control) | Authentication and authorization |

## Quick Start

### Making a Query

```graphql
query GetMyBoards {
  myBoards(limit: 10) {
    id
    title
    description
    isPublic
    createdAt
    owner {
      displayName
    }
    generationCount
  }
}
```

### Creating a Board

```graphql
mutation CreateBoard {
  createBoard(input: {
    title: "My New Board"
    description: "A board for AI-generated art"
    isPublic: false
  }) {
    id
    title
    createdAt
  }
}
```

### Starting a Generation

```graphql
mutation CreateGeneration {
  createGeneration(input: {
    boardId: "board-uuid-here"
    generatorName: "flux-1-dev"
    artifactType: IMAGE
    inputParams: {
      prompt: "A beautiful sunset over mountains"
      width: 1024
      height: 1024
    }
  }) {
    id
    status
    progress
  }
}
```

## Authentication

Most operations require authentication. Include the JWT token in the `Authorization` header:

```http
Authorization: Bearer <your-jwt-token>
```

For multi-tenant deployments, include the tenant identifier:

```http
X-Tenant: <tenant-id>
```

See [Access Control](./graphql-api/access-control) for detailed authentication documentation.

## Schema Introspection

The schema supports introspection, allowing tools like GraphiQL to auto-discover available types and operations:

```graphql
query IntrospectionQuery {
  __schema {
    types {
      name
      description
    }
  }
}
```

## Implementation Details

The GraphQL schema is implemented in `packages/backend/src/boards/graphql/`:

```
graphql/
├── schema.py           # Main schema definition
├── types/              # Type definitions
│   ├── board.py        # Board, BoardMember, BoardRole
│   ├── generation.py   # Generation, ArtifactType, GenerationStatus
│   ├── generator.py    # GeneratorInfo
│   └── user.py         # User
├── queries/
│   └── root.py         # Query root type
├── mutations/
│   └── root.py         # Mutation root type
├── resolvers/          # Field resolvers
│   ├── auth.py
│   ├── board.py
│   ├── generation.py
│   ├── generator.py
│   ├── lineage.py
│   ├── upload.py
│   └── user.py
└── access_control.py   # Authorization helpers
```

## Error Handling

GraphQL errors are returned in the standard format:

```json
{
  "data": null,
  "errors": [
    {
      "message": "Not authenticated",
      "path": ["myBoards"],
      "extensions": {
        "code": "UNAUTHENTICATED"
      }
    }
  ]
}
```

Common error codes:

| Code | Description |
|------|-------------|
| `UNAUTHENTICATED` | Request lacks valid authentication |
| `FORBIDDEN` | User lacks permission for the operation |
| `NOT_FOUND` | Requested resource does not exist |
| `BAD_USER_INPUT` | Invalid input parameters |
| `INTERNAL_SERVER_ERROR` | Server-side error |

## Next Steps

- Learn about [Types](./graphql-api/types) to understand the data model
- Explore available [Queries](./graphql-api/queries) for reading data
- See [Mutations](./graphql-api/mutations) for creating and modifying data
- Understand [Access Control](./graphql-api/access-control) for authentication patterns
