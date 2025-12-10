---
title: Mutations
description: GraphQL mutation operations for the Boards API.
sidebar_position: 3
---

# GraphQL Mutations

This page documents all available GraphQL mutations in the Boards API. Mutations are operations that create, update, or delete data.

## Mutation Overview

| Mutation | Description | Auth Required |
|----------|-------------|---------------|
| [`createBoard`](#createboard) | Create a new board | Yes |
| [`updateBoard`](#updateboard) | Update an existing board | Yes (owner/admin) |
| [`deleteBoard`](#deleteboard) | Delete a board | Yes (owner) |
| [`addBoardMember`](#addboardmember) | Add a member to a board | Yes (owner/admin) |
| [`removeBoardMember`](#removeboardmember) | Remove a member from a board | Yes (owner/admin) |
| [`updateBoardMemberRole`](#updateboardmemberrole) | Change a member's role | Yes (owner/admin) |
| [`createGeneration`](#creategeneration) | Start a new generation | Yes |
| [`cancelGeneration`](#cancelgeneration) | Cancel a pending generation | Yes |
| [`deleteGeneration`](#deletegeneration) | Delete a generation | Yes |
| [`regenerate`](#regenerate) | Re-run a generation | Yes |
| [`uploadArtifact`](#uploadartifact) | Upload an artifact from URL | Yes |

---

## Board Mutations

### createBoard

Create a new board owned by the current user.

```graphql
mutation {
  createBoard(input: CreateBoardInput!): Board!
}
```

#### Input Type

```graphql
input CreateBoardInput {
  title: String!
  description: String
  isPublic: Boolean = false
  settings: JSON
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | `String!` | - | Board title (required) |
| `description` | `String` | `null` | Optional description |
| `isPublic` | `Boolean` | `false` | Whether board is publicly visible |
| `settings` | `JSON` | `null` | Custom board settings |

#### Example

```graphql
mutation CreateMyBoard {
  createBoard(input: {
    title: "AI Art Gallery"
    description: "My collection of AI-generated artwork"
    isPublic: true
    settings: {
      theme: "dark",
      gridColumns: 4
    }
  }) {
    id
    title
    description
    isPublic
    settings
    createdAt
  }
}
```

---

### updateBoard

Update an existing board. Only the owner or admins can update a board.

```graphql
mutation {
  updateBoard(input: UpdateBoardInput!): Board!
}
```

#### Input Type

```graphql
input UpdateBoardInput {
  id: UUID!
  title: String
  description: String
  isPublic: Boolean
  settings: JSON
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID!` | Board ID (required) |
| `title` | `String` | New title |
| `description` | `String` | New description |
| `isPublic` | `Boolean` | New visibility |
| `settings` | `JSON` | New settings (merges with existing) |

#### Example

```graphql
mutation UpdateMyBoard($boardId: UUID!) {
  updateBoard(input: {
    id: $boardId
    title: "Updated Gallery Name"
    isPublic: false
  }) {
    id
    title
    isPublic
    updatedAt
  }
}
```

---

### deleteBoard

Delete a board and all its generations. Only the owner can delete a board.

```graphql
mutation {
  deleteBoard(id: UUID!): Boolean!
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `id` | `UUID!` | Board ID to delete |

#### Returns

`true` if deletion was successful.

#### Example

```graphql
mutation DeleteMyBoard($boardId: UUID!) {
  deleteBoard(id: $boardId)
}
```

:::warning
This operation is destructive and cannot be undone. All generations in the board will also be deleted.
:::

---

### addBoardMember

Add a user as a member of a board. Requires owner or admin role.

```graphql
mutation {
  addBoardMember(input: AddBoardMemberInput!): Board!
}
```

#### Input Type

```graphql
input AddBoardMemberInput {
  boardId: UUID!
  userId: UUID!
  role: BoardRole = VIEWER
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `boardId` | `UUID!` | - | Board to add member to |
| `userId` | `UUID!` | - | User to add |
| `role` | `BoardRole` | `VIEWER` | Role to assign |

#### Example

```graphql
mutation AddMember($boardId: UUID!, $userId: UUID!) {
  addBoardMember(input: {
    boardId: $boardId
    userId: $userId
    role: EDITOR
  }) {
    id
    members {
      user {
        id
        displayName
      }
      role
      joinedAt
    }
  }
}
```

---

### removeBoardMember

Remove a member from a board. Requires owner or admin role.

```graphql
mutation {
  removeBoardMember(boardId: UUID!, userId: UUID!): Board!
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `boardId` | `UUID!` | Board ID |
| `userId` | `UUID!` | User ID to remove |

#### Example

```graphql
mutation RemoveMember($boardId: UUID!, $userId: UUID!) {
  removeBoardMember(boardId: $boardId, userId: $userId) {
    id
    members {
      user {
        id
      }
    }
  }
}
```

---

### updateBoardMemberRole

Change a board member's role. Requires owner or admin role.

```graphql
mutation {
  updateBoardMemberRole(
    boardId: UUID!
    userId: UUID!
    role: BoardRole!
  ): Board!
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `boardId` | `UUID!` | Board ID |
| `userId` | `UUID!` | User ID to update |
| `role` | `BoardRole!` | New role |

#### Example

```graphql
mutation PromoteToAdmin($boardId: UUID!, $userId: UUID!) {
  updateBoardMemberRole(
    boardId: $boardId
    userId: $userId
    role: ADMIN
  ) {
    id
    members {
      user {
        id
      }
      role
    }
  }
}
```

---

## Generation Mutations

### createGeneration

Start a new generation job. The generation runs asynchronously; use subscriptions or polling to track progress.

```graphql
mutation {
  createGeneration(input: CreateGenerationInput!): Generation!
}
```

#### Input Type

```graphql
input CreateGenerationInput {
  boardId: UUID!
  generatorName: String!
  artifactType: ArtifactType!
  inputParams: JSON!
}
```

| Field | Type | Description |
|-------|------|-------------|
| `boardId` | `UUID!` | Board to add the generation to |
| `generatorName` | `String!` | Name of the generator to use |
| `artifactType` | `ArtifactType!` | Type of artifact to generate |
| `inputParams` | `JSON!` | Parameters for the generator (schema varies by generator) |

#### Example

```graphql
mutation GenerateImage($boardId: UUID!) {
  createGeneration(input: {
    boardId: $boardId
    generatorName: "flux-1-dev"
    artifactType: IMAGE
    inputParams: {
      prompt: "A serene mountain landscape at sunset, digital art"
      width: 1024
      height: 768
      num_inference_steps: 28
      guidance_scale: 3.5
    }
  }) {
    id
    status
    progress
    generatorName
    artifactType
    createdAt
  }
}
```

#### Lineage Tracking

Input parameters that reference other generations (by ID) are automatically resolved and tracked as lineage. For example, for image-to-image generation:

```graphql
mutation ImageToImage($boardId: UUID!, $sourceGenId: UUID!) {
  createGeneration(input: {
    boardId: $boardId
    generatorName: "flux-1-dev-img2img"
    artifactType: IMAGE
    inputParams: {
      image: $sourceGenId
      prompt: "Transform to watercolor style"
      strength: 0.75
    }
  }) {
    id
    inputArtifacts {
      role
      generation {
        id
      }
    }
  }
}
```

---

### cancelGeneration

Cancel a pending or processing generation.

```graphql
mutation {
  cancelGeneration(id: UUID!): Generation!
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `id` | `UUID!` | Generation ID to cancel |

#### Returns

The generation with status updated to `CANCELLED`.

#### Example

```graphql
mutation CancelJob($genId: UUID!) {
  cancelGeneration(id: $genId) {
    id
    status
  }
}
```

:::note
Only generations with status `PENDING` or `PROCESSING` can be cancelled. Completed or failed generations cannot be cancelled.
:::

---

### deleteGeneration

Delete a generation and its associated files.

```graphql
mutation {
  deleteGeneration(id: UUID!): Boolean!
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `id` | `UUID!` | Generation ID to delete |

#### Returns

`true` if deletion was successful.

#### Example

```graphql
mutation DeleteGeneration($genId: UUID!) {
  deleteGeneration(id: $genId)
}
```

---

### regenerate

Create a new generation using the same parameters as an existing one.

```graphql
mutation {
  regenerate(id: UUID!): Generation!
}
```

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `id` | `UUID!` | Generation ID to regenerate from |

#### Returns

A new `Generation` with the same parameters but a new ID.

#### Example

```graphql
mutation RegenerateImage($genId: UUID!) {
  regenerate(id: $genId) {
    id
    status
    generatorName
    inputParams
  }
}
```

---

### uploadArtifact

Upload an artifact from an external URL. This creates a generation record for an externally-created asset.

```graphql
mutation {
  uploadArtifact(input: UploadArtifactInput!): Generation!
}
```

#### Input Type

```graphql
input UploadArtifactInput {
  boardId: UUID!
  artifactType: ArtifactType!
  fileUrl: String
  originalFilename: String
  userDescription: String
  parentGenerationId: UUID
}
```

| Field | Type | Description |
|-------|------|-------------|
| `boardId` | `UUID!` | Board to add the artifact to |
| `artifactType` | `ArtifactType!` | Type of the artifact |
| `fileUrl` | `String` | URL to fetch the file from |
| `originalFilename` | `String` | Original filename |
| `userDescription` | `String` | User-provided description |
| `parentGenerationId` | `UUID` | Optional parent generation for lineage |

#### Example

```graphql
mutation UploadImage($boardId: UUID!) {
  uploadArtifact(input: {
    boardId: $boardId
    artifactType: IMAGE
    fileUrl: "https://example.com/my-image.png"
    originalFilename: "my-image.png"
    userDescription: "Reference image for style transfer"
  }) {
    id
    status
    storageUrl
    thumbnailUrl
  }
}
```

---

## Error Handling

Mutations return errors in the standard GraphQL format:

```json
{
  "data": {
    "createBoard": null
  },
  "errors": [
    {
      "message": "Not authenticated",
      "path": ["createBoard"],
      "extensions": {
        "code": "UNAUTHENTICATED"
      }
    }
  ]
}
```

### Common Errors

| Code | Description |
|------|-------------|
| `UNAUTHENTICATED` | No valid authentication token |
| `FORBIDDEN` | User lacks permission for this operation |
| `NOT_FOUND` | Referenced resource doesn't exist |
| `BAD_USER_INPUT` | Invalid input parameters |

---

## Source Files

Mutation definitions are implemented in:

- `packages/backend/src/boards/graphql/mutations/root.py`
- `packages/backend/src/boards/graphql/resolvers/`
