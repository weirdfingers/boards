---
title: Queries
description: GraphQL query operations for the Boards API.
sidebar_position: 2
---

# GraphQL Queries

This page documents all available GraphQL queries in the Boards API. Queries are read-only operations for fetching data.

## Query Overview

| Query | Description | Auth Required |
|-------|-------------|---------------|
| [`me`](#me) | Get current authenticated user | Yes |
| [`user`](#user) | Get user by ID | Yes |
| [`board`](#board) | Get board by ID | Depends* |
| [`myBoards`](#myboards) | Get boards owned by or shared with current user | Yes |
| [`publicBoards`](#publicboards) | Get public boards | No |
| [`searchBoards`](#searchboards) | Search boards by title/description | Yes |
| [`generation`](#generation) | Get generation by ID | Depends* |
| [`recentGenerations`](#recentgenerations) | Get recent generations with filters | Yes |
| [`generators`](#generators) | Get available generators | No |

*Depends on board visibility (public boards accessible without auth)

---

## User Queries

### me

Get the currently authenticated user.

```graphql
query {
  me: User
}
```

#### Returns

`User` or `null` if not authenticated.

#### Example

```graphql
query GetCurrentUser {
  me {
    id
    email
    displayName
    avatarUrl
    createdAt
  }
}
```

#### Response

```json
{
  "data": {
    "me": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "displayName": "John Doe",
      "avatarUrl": "https://example.com/avatar.jpg",
      "createdAt": "2024-01-15T10:30:00Z"
    }
  }
}
```

---

### user

Get a user by their ID.

```graphql
query {
  user(id: UUID!): User
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `id` | `UUID!` | The user's unique identifier |

#### Returns

`User` or `null` if not found.

#### Example

```graphql
query GetUser($userId: UUID!) {
  user(id: $userId) {
    id
    displayName
    avatarUrl
    boards {
      id
      title
      isPublic
    }
  }
}
```

---

## Board Queries

### board

Get a single board by ID. Returns the board if it's public or if the authenticated user has access.

```graphql
query {
  board(id: UUID!): Board
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `id` | `UUID!` | The board's unique identifier |

#### Returns

`Board` or `null` if not found or not accessible.

#### Example

```graphql
query GetBoard($boardId: UUID!) {
  board(id: $boardId) {
    id
    title
    description
    isPublic
    createdAt
    updatedAt
    owner {
      id
      displayName
    }
    members {
      user {
        displayName
      }
      role
      joinedAt
    }
    generationCount
    generations(limit: 20) {
      id
      thumbnailUrl
      artifactType
      status
      createdAt
    }
  }
}
```

---

### myBoards

Get boards owned by or shared with the current authenticated user.

```graphql
query {
  myBoards(
    limit: Int = 50
    offset: Int = 0
    role: BoardQueryRole
    sort: SortOrder
  ): [Board!]!
}
```

#### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `limit` | `Int` | `50` | Maximum number of boards to return |
| `offset` | `Int` | `0` | Number of boards to skip |
| `role` | `BoardQueryRole` | `ANY` | Filter by user's role |
| `sort` | `SortOrder` | `UPDATED_DESC` | Sort order |

#### Enums

**BoardQueryRole:**

| Value | Description |
|-------|-------------|
| `ANY` | All accessible boards |
| `OWNER` | Only boards user owns |
| `MEMBER` | Only boards where user is a member (not owner) |

**SortOrder:**

| Value | Description |
|-------|-------------|
| `CREATED_ASC` | Oldest first |
| `CREATED_DESC` | Newest first |
| `UPDATED_ASC` | Least recently updated first |
| `UPDATED_DESC` | Most recently updated first |

#### Example

```graphql
query GetMyBoards {
  myBoards(limit: 10, role: OWNER, sort: UPDATED_DESC) {
    id
    title
    description
    isPublic
    updatedAt
    generationCount
  }
}
```

---

### publicBoards

Get publicly visible boards.

```graphql
query {
  publicBoards(
    limit: Int = 50
    offset: Int = 0
    sort: SortOrder
  ): [Board!]!
}
```

#### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `limit` | `Int` | `50` | Maximum number of boards to return |
| `offset` | `Int` | `0` | Number of boards to skip |
| `sort` | `SortOrder` | `UPDATED_DESC` | Sort order |

#### Example

```graphql
query GetPublicBoards {
  publicBoards(limit: 20, sort: CREATED_DESC) {
    id
    title
    description
    owner {
      displayName
    }
    generationCount
    createdAt
  }
}
```

---

### searchBoards

Search for boards by title or description. Only returns boards accessible to the current user.

```graphql
query {
  searchBoards(
    query: String!
    limit: Int = 50
    offset: Int = 0
  ): [Board!]!
}
```

#### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `query` | `String!` | - | Search query string |
| `limit` | `Int` | `50` | Maximum number of boards to return |
| `offset` | `Int` | `0` | Number of boards to skip |

#### Example

```graphql
query SearchBoards($searchQuery: String!) {
  searchBoards(query: $searchQuery, limit: 10) {
    id
    title
    description
    isPublic
    owner {
      displayName
    }
  }
}
```

---

## Generation Queries

### generation

Get a single generation by ID.

```graphql
query {
  generation(id: UUID!): Generation
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `id` | `UUID!` | The generation's unique identifier |

#### Returns

`Generation` or `null` if not found or not accessible.

#### Example

```graphql
query GetGeneration($genId: UUID!) {
  generation(id: $genId) {
    id
    generatorName
    artifactType
    status
    progress
    errorMessage
    storageUrl
    thumbnailUrl
    inputParams
    outputMetadata
    createdAt
    startedAt
    completedAt
    user {
      displayName
    }
    board {
      id
      title
    }
    inputArtifacts {
      role
      artifactType
      generation {
        id
        thumbnailUrl
      }
    }
  }
}
```

---

### recentGenerations

Get recent generations with optional filters.

```graphql
query {
  recentGenerations(
    boardId: UUID
    status: GenerationStatus
    artifactType: ArtifactType
    limit: Int = 50
    offset: Int = 0
  ): [Generation!]!
}
```

#### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `boardId` | `UUID` | - | Filter by board |
| `status` | `GenerationStatus` | - | Filter by status |
| `artifactType` | `ArtifactType` | - | Filter by artifact type |
| `limit` | `Int` | `50` | Maximum number to return |
| `offset` | `Int` | `0` | Number to skip |

#### Example

```graphql
query GetRecentImages($boardId: UUID!) {
  recentGenerations(
    boardId: $boardId
    artifactType: IMAGE
    status: COMPLETED
    limit: 20
  ) {
    id
    generatorName
    storageUrl
    thumbnailUrl
    inputParams
    createdAt
  }
}
```

---

## Generator Queries

### generators

Get all available generators, optionally filtered by artifact type.

```graphql
query {
  generators(artifactType: String): [GeneratorInfo!]!
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `artifactType` | `String` | Filter by artifact type (e.g., "image", "video") |

#### Example

```graphql
query GetImageGenerators {
  generators(artifactType: "image") {
    name
    description
    artifactType
    inputSchema
  }
}
```

#### Response

```json
{
  "data": {
    "generators": [
      {
        "name": "flux-1-dev",
        "description": "FLUX.1 Dev - High quality image generation",
        "artifactType": "IMAGE",
        "inputSchema": {
          "type": "object",
          "properties": {
            "prompt": {
              "type": "string",
              "description": "Text prompt for image generation"
            },
            "width": {
              "type": "integer",
              "default": 1024
            },
            "height": {
              "type": "integer",
              "default": 1024
            }
          },
          "required": ["prompt"]
        }
      }
    ]
  }
}
```

---

## Pagination

All list queries support pagination via `limit` and `offset` arguments:

```graphql
query PaginatedBoards($page: Int!) {
  myBoards(limit: 10, offset: $page * 10) {
    id
    title
  }
}
```

For large datasets, consider using cursor-based pagination patterns in your application layer.

---

## Error Handling

Queries return `null` for single-item queries when:
- The resource doesn't exist
- The user doesn't have permission to access it

List queries return empty arrays when no results match.

Authentication errors are returned in the `errors` array:

```json
{
  "data": {
    "myBoards": null
  },
  "errors": [
    {
      "message": "Not authenticated",
      "path": ["myBoards"]
    }
  ]
}
```

---

## Source Files

Query definitions are implemented in:

- `packages/backend/src/boards/graphql/queries/root.py`
- `packages/backend/src/boards/graphql/resolvers/`
