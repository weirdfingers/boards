# Auth & Authorization (Pluggable)

## Goals
- Support multiple auth providers without forking app code.
- Keep the **hooks** API stable; swap providers via configuration.

## Backend
- Auth adapter interface: `verify_token() -> Principal`, `issue_token()?`, `get_user_info()`.
- Built-in adapters: Supabase Auth (JWT), Clerk (JWT), Auth0 (OIDC/JWT), custom OIDC.
- Map `Principal` to local `users` row on first-seen (just-in-time provisioning).

## Frontend
- `useAuth()` hook wraps provider SDK or backend session API:
  - `user`, `status`, `signIn()`, `signOut()`, `getToken()`
- Provider packages: `@toolkit/auth-supabase`, `@toolkit/auth-clerk`, `@toolkit/auth-auth0` implementing the same interface.

## Authorization
- Board-scoped RBAC: owner/editor/viewer in `board_members`.
- Future: optional relationship-based access (OpenFGA) behind an interface.
