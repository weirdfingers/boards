---
title: Types
description: GraphQL type definitions for the Boards API.
sidebar_position: 1
---

# GraphQL Types

This page documents all GraphQL types available in the Boards API. Types are organized by domain: Boards, Generations, Generators, and Users.

## Type Overview

| Type | Description |
|------|-------------|
| [`Board`](#board) | A collection of generations |
| [`BoardMember`](#boardmember) | A user's membership in a board |
| [`BoardRole`](#boardrole) | Enum for member permissions |
| [`Generation`](#generation) | An AI-generated artifact |
| [`GenerationStatus`](#generationstatus) | Enum for generation states |
| [`ArtifactType`](#artifacttype) | Enum for content types |
| [`ArtifactLineage`](#artifactlineage) | Input artifact relationship |
| [`AncestryNode`](#ancestrynode) | Node in ancestry tree |
| [`DescendantNode`](#descendantnode) | Node in descendants tree |
| [`AdditionalFile`](#additionalfile) | Extra files from generation |
| [`GeneratorInfo`](#generatorinfo) | Available generator metadata |
| [`User`](#user) | User account information |

---

## Board Types

### Board

A board is a collection of AI-generated content. Boards can be public or private, and support collaborative access through board members.

```graphql
type Board {
  id: UUID!
  tenantId: UUID!
  ownerId: UUID!
  title: String!
  description: String
  isPublic: Boolean!
  settings: JSON!
  metadata: JSON!
  createdAt: DateTime!
  updatedAt: DateTime!

  # Resolved fields
  owner: User!
  members: [BoardMember!]!
  generations(limit: Int = 50, offset: Int = 0): [Generation!]!
  generationCount: Int!
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID!` | Unique identifier |
| `tenantId` | `UUID!` | Tenant the board belongs to |
| `ownerId` | `UUID!` | ID of the board owner |
| `title` | `String!` | Board title |
| `description` | `String` | Optional description |
| `isPublic` | `Boolean!` | Whether the board is publicly visible |
| `settings` | `JSON!` | Board-specific settings |
| `metadata` | `JSON!` | Additional metadata |
| `createdAt` | `DateTime!` | Creation timestamp |
| `updatedAt` | `DateTime!` | Last update timestamp |
| `owner` | `User!` | The user who owns the board |
| `members` | `[BoardMember!]!` | Users with access to this board |
| `generations` | `[Generation!]!` | Generations in this board (paginated) |
| `generationCount` | `Int!` | Total number of generations |

#### Example Query

```graphql
query GetBoard($id: UUID!) {
  board(id: $id) {
    id
    title
    description
    isPublic
    owner {
      displayName
      avatarUrl
    }
    members {
      user {
        displayName
      }
      role
    }
    generationCount
    generations(limit: 10) {
      id
      thumbnailUrl
      artifactType
    }
  }
}
```

---

### BoardMember

Represents a user's membership in a board with their assigned role.

```graphql
type BoardMember {
  id: UUID!
  boardId: UUID!
  userId: UUID!
  role: BoardRole!
  invitedBy: UUID
  joinedAt: DateTime!

  # Resolved fields
  user: User!
  inviter: User
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID!` | Unique identifier |
| `boardId` | `UUID!` | ID of the board |
| `userId` | `UUID!` | ID of the member user |
| `role` | `BoardRole!` | Member's permission level |
| `invitedBy` | `UUID` | ID of user who sent the invite |
| `joinedAt` | `DateTime!` | When the user joined |
| `user` | `User!` | The member's user object |
| `inviter` | `User` | User who invited this member |

---

### BoardRole

Enumeration of possible board member roles.

```graphql
enum BoardRole {
  VIEWER
  EDITOR
  ADMIN
}
```

| Value | Description |
|-------|-------------|
| `VIEWER` | Can view board content |
| `EDITOR` | Can view and create generations |
| `ADMIN` | Full access including member management |

---

## Generation Types

### Generation

A generation represents an AI-generated artifact (image, video, audio, text, etc.) with its input parameters, output files, and lineage information.

```graphql
type Generation {
  id: UUID!
  tenantId: UUID!
  boardId: UUID!
  userId: UUID!

  # Generation details
  generatorName: String!
  artifactType: ArtifactType!

  # Storage
  storageUrl: String
  thumbnailUrl: String
  additionalFiles: [AdditionalFile!]!

  # Parameters and metadata
  inputParams: JSON!
  outputMetadata: JSON!

  # Job tracking
  externalJobId: String
  status: GenerationStatus!
  progress: Float!
  errorMessage: String

  # Timestamps
  startedAt: DateTime
  completedAt: DateTime
  createdAt: DateTime!
  updatedAt: DateTime!

  # Resolved fields
  board: Board!
  user: User!
  inputArtifacts: [ArtifactLineage!]!
  ancestry(maxDepth: Int = 25): AncestryNode!
  descendants(maxDepth: Int = 25): DescendantNode!
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID!` | Unique identifier |
| `tenantId` | `UUID!` | Tenant this generation belongs to |
| `boardId` | `UUID!` | Board containing this generation |
| `userId` | `UUID!` | User who created this generation |
| `generatorName` | `String!` | Name of the generator used |
| `artifactType` | `ArtifactType!` | Type of content generated |
| `storageUrl` | `String` | URL to the generated artifact |
| `thumbnailUrl` | `String` | URL to thumbnail (for images/videos) |
| `additionalFiles` | `[AdditionalFile!]!` | Extra output files |
| `inputParams` | `JSON!` | Parameters passed to the generator |
| `outputMetadata` | `JSON!` | Metadata from the generation |
| `externalJobId` | `String` | ID from external generation service |
| `status` | `GenerationStatus!` | Current job status |
| `progress` | `Float!` | Progress (0.0 to 1.0) |
| `errorMessage` | `String` | Error details if failed |
| `startedAt` | `DateTime` | When processing started |
| `completedAt` | `DateTime` | When processing finished |
| `createdAt` | `DateTime!` | When the job was created |
| `updatedAt` | `DateTime!` | Last update time |
| `board` | `Board!` | The board this belongs to |
| `user` | `User!` | User who created this |
| `inputArtifacts` | `[ArtifactLineage!]!` | Input artifacts with roles |
| `ancestry` | `AncestryNode!` | Full ancestry tree |
| `descendants` | `DescendantNode!` | All derived generations |

#### Example Query

```graphql
query GetGeneration($id: UUID!) {
  generation(id: $id) {
    id
    generatorName
    artifactType
    status
    progress
    storageUrl
    thumbnailUrl
    inputParams
    outputMetadata
    createdAt
    completedAt
    user {
      displayName
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

### GenerationStatus

Enumeration of generation job states.

```graphql
enum GenerationStatus {
  PENDING
  PROCESSING
  COMPLETED
  FAILED
  CANCELLED
}
```

| Value | Description |
|-------|-------------|
| `PENDING` | Job is queued, waiting to start |
| `PROCESSING` | Job is currently running |
| `COMPLETED` | Job finished successfully |
| `FAILED` | Job encountered an error |
| `CANCELLED` | Job was cancelled by user |

---

### ArtifactType

Enumeration of supported artifact content types.

```graphql
enum ArtifactType {
  IMAGE
  VIDEO
  AUDIO
  TEXT
  LORA
  MODEL
}
```

| Value | Description |
|-------|-------------|
| `IMAGE` | Static image (PNG, JPEG, WebP, etc.) |
| `VIDEO` | Video file (MP4, WebM, etc.) |
| `AUDIO` | Audio file (MP3, WAV, etc.) |
| `TEXT` | Text content |
| `LORA` | LoRA model weights |
| `MODEL` | Full model weights |

---

### ArtifactLineage

Represents a relationship between a generation and one of its input artifacts.

```graphql
type ArtifactLineage {
  generationId: UUID!
  role: String!
  artifactType: ArtifactType!

  # Resolved fields
  generation: Generation
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `generationId` | `UUID!` | ID of the input generation |
| `role` | `String!` | Role of this input (e.g., "image", "mask", "reference") |
| `artifactType` | `ArtifactType!` | Type of the input artifact |
| `generation` | `Generation` | Full generation object |

---

### AncestryNode

Represents a node in the ancestry tree, showing all inputs that led to a generation.

```graphql
type AncestryNode {
  generation: Generation!
  depth: Int!
  role: String
  parents: [AncestryNode!]!
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `generation` | `Generation!` | The generation at this node |
| `depth` | `Int!` | Depth in the tree (0 = root) |
| `role` | `String` | Role this generation played as input |
| `parents` | `[AncestryNode!]!` | Parent nodes (inputs to this generation) |

---

### DescendantNode

Represents a node in the descendants tree, showing all generations derived from an artifact.

```graphql
type DescendantNode {
  generation: Generation!
  depth: Int!
  role: String
  children: [DescendantNode!]!
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `generation` | `Generation!` | The generation at this node |
| `depth` | `Int!` | Depth in the tree (0 = root) |
| `role` | `String` | Role the parent played for this generation |
| `children` | `[DescendantNode!]!` | Child nodes (generations using this as input) |

---

### AdditionalFile

Represents an additional file produced by a generation (e.g., depth maps, masks).

```graphql
type AdditionalFile {
  url: String!
  type: String!
  metadata: JSON!
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `url` | `String!` | URL to the file |
| `type` | `String!` | File type identifier |
| `metadata` | `JSON!` | Additional file metadata |

---

## Generator Types

### GeneratorInfo

Information about an available generator.

```graphql
type GeneratorInfo {
  name: String!
  description: String!
  artifactType: ArtifactType!
  inputSchema: JSON!
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `String!` | Unique generator identifier |
| `description` | `String!` | Human-readable description |
| `artifactType` | `ArtifactType!` | Type of content this generator produces |
| `inputSchema` | `JSON!` | JSON Schema for input parameters |

#### Example Query

```graphql
query GetGenerators {
  generators {
    name
    description
    artifactType
    inputSchema
  }
}
```

---

## User Types

### User

Represents a user account in the system.

```graphql
type User {
  id: UUID!
  tenantId: UUID!
  authProvider: String!
  authSubject: String!
  email: String
  displayName: String
  avatarUrl: String
  createdAt: DateTime!
  updatedAt: DateTime!

  # Resolved fields
  boards: [Board!]!
  memberBoards: [Board!]!
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID!` | Unique identifier |
| `tenantId` | `UUID!` | Tenant this user belongs to |
| `authProvider` | `String!` | Authentication provider (supabase, clerk, etc.) |
| `authSubject` | `String!` | Subject ID from the auth provider |
| `email` | `String` | User's email address |
| `displayName` | `String` | Display name |
| `avatarUrl` | `String` | URL to avatar image |
| `createdAt` | `DateTime!` | Account creation time |
| `updatedAt` | `DateTime!` | Last update time |
| `boards` | `[Board!]!` | Boards owned by this user |
| `memberBoards` | `[Board!]!` | Boards where user is a member |

#### Example Query

```graphql
query GetCurrentUser {
  me {
    id
    email
    displayName
    avatarUrl
    boards {
      id
      title
    }
    memberBoards {
      id
      title
      owner {
        displayName
      }
    }
  }
}
```

---

## Scalar Types

The API uses the following scalar types:

| Scalar | Description |
|--------|-------------|
| `UUID` | UUID string (e.g., `"550e8400-e29b-41d4-a716-446655440000"`) |
| `DateTime` | ISO 8601 datetime string (e.g., `"2024-01-15T10:30:00Z"`) |
| `JSON` | Arbitrary JSON object |

## Source Files

Type definitions are implemented in:

- `packages/backend/src/boards/graphql/types/board.py`
- `packages/backend/src/boards/graphql/types/generation.py`
- `packages/backend/src/boards/graphql/types/generator.py`
- `packages/backend/src/boards/graphql/types/user.py`
