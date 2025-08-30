# Auth & Authorization - Detailed Design

## Objectives
- Provide a pluggable authentication layer (Supabase Auth, Clerk, Auth0, custom OIDC/JWT) without app code forks.
- Keep frontend hooks interface stable: `useAuth()` drives session and tokens regardless of provider.
- Implement board-scoped RBAC with clear, enforceable rules on both backend resolvers and storage access.
- Support multi-tenancy and just-in-time user provisioning.
- Allow future optional shift to relationship-based authorization (e.g., OpenFGA) behind an interface.

## Terminology
- Principal: The identity extracted from an incoming token (provider, subject, email, claims).
- User: Local row in `users` bound to a `(tenant_id, auth_provider, auth_subject)`.
- Session: The runtime context (in GraphQL/REST) containing the authenticated user and tenant.

## High-level Architecture
- Backend exposes a provider-agnostic `AuthAdapter` interface.
- FastAPI + Strawberry inject a `AuthContext` into request/GraphQL context via middleware.
- JIT provisioning: on first-seen principal, create a `users` row within current tenant.
- Authorization gates applied in:
  - GraphQL field resolvers and mutations
  - REST endpoints (SSE, webhooks, storage)
  - Storage presign issuance

## Backend: Interfaces and Flow

### AuthAdapter Interface
```python
class Principal(TypedDict):
    provider: str            # 'supabase' | 'clerk' | 'auth0' | 'oidc' | 'jwt'
    subject: str             # provider user id (sub)
    email: NotRequired[str]
    display_name: NotRequired[str]
    avatar_url: NotRequired[str]
    claims: NotRequired[dict]

class AuthAdapter(Protocol):
    async def verify_token(self, token: str) -> Principal: ...
    async def issue_token(self, user_id: UUID | None = None, claims: dict | None = None) -> str: ...  # optional
    async def get_user_info(self, token: str) -> dict: ...  # provider-specific enrichment (optional)
```

- Built-ins: `SupabaseAuthAdapter`, `ClerkAuthAdapter`, `Auth0OIDCAdapter`, `JWTAdapter`.
- Adapter selection: `settings.auth_provider` and `settings.auth_config`.

### Request Auth Flow
1. Client attaches `Authorization: Bearer <token>` to GraphQL/REST.
2. `AuthMiddleware` extracts token, calls `adapter.verify_token` → `Principal`.
3. Resolve tenant: `X-Tenant` header or mapped domain; default single-tenant.
4. JIT Provisioning: `ensure_local_user(tenant_id, principal)` creates or fetches `users` row.
5. Context: `AuthContext(user, tenant, principal, token)` attached to request and GraphQL `info.context`.

### Data Model Alignment
- Uses `users(tenant_id, auth_provider, auth_subject, email, display_name, avatar_url, metadata)`.
- RBAC via `board_members(board_id, user_id, role)` with roles: `owner`, `editor`, `viewer`.
- Enforce tenant isolation by filtering queries on `tenant_id`.

## Authorization: RBAC Policy

### Roles
- owner: full control; manage members; delete board; manage generations.
- editor: create/update generations; edit board metadata; invite/remove members of lower role if allowed.
- viewer: read-only access to board and generations.

### Permission Matrix (selected)
- Board
  - create: authenticated user → owner of new board
  - read: owner/editor/viewer OR `boards.is_public = true`
  - update: owner or editor
  - delete: owner
  - members: owner or editor (read); manage: owner
- Generation
  - create: editor or owner on target board
  - read: viewer/editor/owner, or public board
  - cancel/delete: owner or editor if created by self; owner can manage all

### Enforcement Points
- GraphQL resolvers and mutations must call helpers:
```python
async def require_board_role(db, board_id: UUID, user_id: UUID, roles: set[str]): ...
async def can_read_board(db, board_id: UUID, user_id: UUID | None) -> bool: ...
```
- Storage presigned URLs only issued if `can_read_board`/`require_board_role` passes.
- SSE streams for job progress validate `can_read_board`.

## Backend Integration in Strawberry/FastAPI

### Context Injection
```python
# graphql/schema.py
from strawberry.fastapi import GraphQLRouter

async def get_context_dependency(request: Request) -> dict:
    return {
        "auth": request.state.auth_context,  # AuthContext
        "db": request.state.db,
    }

router = GraphQLRouter(schema, context_getter=get_context_dependency)
```

### Resolver Usage
```python
@strawberry.type
class Query:
    @strawberry.field
    async def board(self, info, id: UUID) -> Optional[Board]:
        auth = info.context["auth"]
        if not await can_read_board(info.context["db"], id, auth.user.id if auth.user else None):
            raise PermissionError("Not authorized")
        return await boards_repo.get_by_id(id)
```

### Mutations
- `create_board`: authenticated required; set `owner_id = auth.user.id` and `tenant_id`.
- `add_board_member`, `update_board_member_role`, `remove_board_member`: require owner.
- `create_generation`: require `editor` or `owner` on `board_id`.

## Frontend: `useAuth()` and Providers

### Stable Hook Contract
```ts
interface AuthState {
  user: {
    id: string
    email?: string
    displayName?: string
    avatarUrl?: string
    provider: string
    subject: string
  } | null
  status: 'unauthenticated' | 'loading' | 'authenticated'
  signIn: (opts?: Record<string, unknown>) => Promise<void>
  signOut: () => Promise<void>
  getToken: () => Promise<string | null>
}
```

- Implementations:
  - `@toolkit/auth-supabase`: wraps Supabase JS; maps session user → above shape.
  - `@toolkit/auth-clerk`: wraps Clerk JS.
  - `@toolkit/auth-auth0`: wraps Auth0 SPA SDK.
  - `@toolkit/auth-jwt`: local token storage with backend-issued JWT.

### Token Wiring
- Apollo/urql `authLink` calls `getToken()`.
- SSR/Next.js: support token storage via cookies; `getToken` reads from cookie when in server context.

### Multi-tenant Header
- Client attaches `X-Tenant` (slug) when applicable.

## Edge Cases & Considerations
- Anonymous read for public boards: no token required; bypass JIT user creation.
- Tenant mismatch: forbid cross-tenant access even if same provider subject.
- Revocation: adapters may validate via provider introspection when possible.
- Clock skew and token expiry: adapters must handle grace periods and refresh (frontend providers manage refresh, backend validates exp/nbf).
- Webhooks: signed provider hooks; execute minimal operations without end-user auth.
- Rate limiting: optional per-user/per-tenant throttles on mutations.

## Testing Strategy
- Unit tests for each adapter with sample tokens/claims.
- Integration tests: end-to-end sign-in via mocked provider → JIT user → RBAC checks on queries/mutations.
- Property tests for authorization helpers to ensure no privilege escalation.

## Migration & Backward Compatibility
- DB already contains `users` and `board_members` tables as defined.
- If migrating from single-provider to multi-provider, backfill `auth_provider` and `auth_subject`.
- Keep GraphQL schema stable; auth only influences access, not type shapes.

## Future: Relationship-based Authorization
- Introduce `AuthorizationEngine` interface with a default RBAC engine.
- Optional OpenFGA engine implements the same `can_read_board/require_role` semantics, allowing gradual adoption.

## Configuration
- `BOARDS_AUTH_PROVIDER` in env; `BOARDS_AUTH_CONFIG` JSON for provider details.
- Providers may require redirect URIs, JWKS endpoints, or domain configuration.

## Operational Notes
- Observability: log `tenant_id`, `user_id`, and decision outcomes (allow/deny) with reasons.
- PII: avoid logging raw tokens; store minimal user profile; allow metadata enrichment opt-in.
- Secrets: use platform secrets manager; never store provider API secrets in DB unencrypted.