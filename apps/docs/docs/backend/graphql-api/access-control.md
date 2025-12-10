---
title: Access Control
description: Authentication and authorization for the Boards GraphQL API.
sidebar_position: 4
---

# Access Control

This page documents how authentication and authorization work in the Boards GraphQL API.

## Overview

The Boards API uses a layered security model:

1. **Authentication** - Verifying user identity via JWT tokens
2. **Authorization** - Checking permissions for specific operations
3. **Multi-tenancy** - Isolating data between tenants

## Authentication

### Request Headers

Include authentication credentials in HTTP headers:

```http
POST /graphql HTTP/1.1
Authorization: Bearer <jwt-token>
X-Tenant: <tenant-id>
Content-Type: application/json
```

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes* | JWT bearer token |
| `X-Tenant` | Depends | Tenant identifier (for multi-tenant deployments) |

*Required for authenticated operations. Public queries work without authentication.

### JWT Token Format

The API expects standard JWT tokens with these claims:

```json
{
  "sub": "user-unique-id",
  "email": "user@example.com",
  "iat": 1704067200,
  "exp": 1704153600
}
```

| Claim | Description |
|-------|-------------|
| `sub` | Subject - unique user identifier from auth provider |
| `email` | User's email address |
| `iat` | Issued at timestamp |
| `exp` | Expiration timestamp |

### Auth Providers

Boards supports multiple authentication providers:

| Provider | Configuration | Description |
|----------|---------------|-------------|
| `none` | `BOARDS_AUTH_PROVIDER=none` | No authentication (development only) |
| `jwt` | `BOARDS_AUTH_PROVIDER=jwt` | Generic JWT validation |
| `supabase` | `BOARDS_AUTH_PROVIDER=supabase` | Supabase Auth integration |

See [Auth Providers](/docs/auth/providers/jwt) for detailed configuration.

---

## Authorization

### Permission Model

Authorization is based on user relationships to resources:

```
User
 ├── Owns Boards (owner_id)
 └── Member of Boards (board_members)
       └── Has Role (VIEWER, EDITOR, ADMIN)
```

### Board Access Rules

Access to boards is determined by:

1. **Public boards** - Accessible to everyone (read-only without auth)
2. **Owner** - Full access to all operations
3. **Admin member** - Can manage members and edit
4. **Editor member** - Can create generations
5. **Viewer member** - Read-only access

```python
def can_access_board(board, auth_context):
    # Public boards are accessible to everyone
    if board.is_public:
        return True

    # Private boards require authentication
    if not auth_context.is_authenticated:
        return False

    # Owner has access
    if board.owner_id == auth_context.user_id:
        return True

    # Check membership
    return any(
        member.user_id == auth_context.user_id
        for member in board.board_members
    )
```

### Query Authorization

| Query | Auth Required | Access Rule |
|-------|---------------|-------------|
| `me` | Yes | Returns authenticated user |
| `user` | Yes | Any authenticated user |
| `board` | Depends | Public or user has access |
| `myBoards` | Yes | Owned or member boards |
| `publicBoards` | No | All public boards |
| `searchBoards` | Yes | Accessible boards only |
| `generation` | Depends | Board access required |
| `recentGenerations` | Yes | Accessible boards only |
| `generators` | No | Public information |

### Mutation Authorization

| Mutation | Required Role |
|----------|---------------|
| `createBoard` | Authenticated |
| `updateBoard` | Owner or Admin |
| `deleteBoard` | Owner only |
| `addBoardMember` | Owner or Admin |
| `removeBoardMember` | Owner or Admin |
| `updateBoardMemberRole` | Owner or Admin |
| `createGeneration` | Owner, Admin, or Editor |
| `cancelGeneration` | Creator, Owner, or Admin |
| `deleteGeneration` | Creator, Owner, or Admin |
| `regenerate` | Owner, Admin, or Editor |
| `uploadArtifact` | Owner, Admin, or Editor |

---

## Board Roles

### BoardRole Enum

```graphql
enum BoardRole {
  VIEWER
  EDITOR
  ADMIN
}
```

### Role Permissions

| Permission | Viewer | Editor | Admin | Owner |
|------------|--------|--------|-------|-------|
| View board | Yes | Yes | Yes | Yes |
| View generations | Yes | Yes | Yes | Yes |
| Create generations | No | Yes | Yes | Yes |
| Delete own generations | No | Yes | Yes | Yes |
| Delete any generation | No | No | Yes | Yes |
| Add members | No | No | Yes | Yes |
| Remove members | No | No | Yes | Yes |
| Update member roles | No | No | Yes | Yes |
| Update board settings | No | No | Yes | Yes |
| Delete board | No | No | No | Yes |

---

## Query Filters

### BoardQueryRole

Filter boards by your relationship:

```graphql
enum BoardQueryRole {
  ANY      # All accessible boards
  OWNER    # Only boards you own
  MEMBER   # Only boards where you're a member (not owner)
}
```

#### Example

```graphql
query GetOwnedBoards {
  myBoards(role: OWNER) {
    id
    title
  }
}

query GetSharedBoards {
  myBoards(role: MEMBER) {
    id
    title
    owner {
      displayName
    }
  }
}
```

### SortOrder

Sort results by creation or update time:

```graphql
enum SortOrder {
  CREATED_ASC    # Oldest first
  CREATED_DESC   # Newest first
  UPDATED_ASC    # Least recently updated
  UPDATED_DESC   # Most recently updated
}
```

---

## Multi-Tenancy

### Tenant Isolation

In multi-tenant deployments, all data is scoped to a tenant:

- Users belong to a tenant
- Boards belong to a tenant
- Generations belong to a tenant

Cross-tenant access is never permitted.

### Specifying Tenant

Include the `X-Tenant` header:

```http
X-Tenant: my-tenant-id
```

Or use a subdomain (if configured):

```
https://my-tenant.boards.example.com/graphql
```

See [Multi-Tenancy](/docs/auth/multi-tenant) for detailed configuration.

---

## Error Responses

### Authentication Errors

```json
{
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

### Authorization Errors

```json
{
  "errors": [
    {
      "message": "You don't have permission to access this board",
      "path": ["board"],
      "extensions": {
        "code": "FORBIDDEN"
      }
    }
  ]
}
```

### Invalid Token

```json
{
  "errors": [
    {
      "message": "Invalid or expired token",
      "path": ["me"],
      "extensions": {
        "code": "UNAUTHENTICATED"
      }
    }
  ]
}
```

---

## Security Best Practices

### Client-Side

1. **Store tokens securely** - Use httpOnly cookies or secure storage
2. **Handle expiration** - Refresh tokens before they expire
3. **Validate responses** - Check for auth errors and redirect to login

### Server-Side

1. **Validate all inputs** - Never trust client data
2. **Use parameterized queries** - Prevent injection attacks
3. **Log access attempts** - Audit sensitive operations
4. **Rate limit** - Prevent brute force attacks

---

## Implementation Details

Access control logic is implemented in:

- `packages/backend/src/boards/graphql/access_control.py` - Core authorization functions
- `packages/backend/src/boards/auth/` - Authentication providers
- `packages/backend/src/boards/auth/middleware.py` - Request middleware

### Key Functions

```python
# Get auth context from GraphQL info
async def get_auth_context_from_info(info: strawberry.Info) -> AuthContext | None

# Check if user can access a board
def can_access_board(board: Boards, auth_context: AuthContext | None) -> bool

# Check if user is owner or member
def is_board_owner_or_member(board: Boards, auth_context: AuthContext | None) -> bool
```

---

## Related Documentation

- [Auth Overview](/docs/auth/overview)
- [Auth Providers](/docs/auth/providers/jwt)
- [Multi-Tenancy](/docs/auth/multi-tenant)
- [Backend Authorization](/docs/auth/backend/authorization)
