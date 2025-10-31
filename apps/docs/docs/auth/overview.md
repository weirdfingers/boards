# Authentication & Authorization

Boards provides a flexible, pluggable authentication system that supports multiple auth providers while maintaining a consistent interface for your application code.

## Key Features

- **Provider-agnostic**: Support for Supabase, Clerk, Auth0, custom JWT, and OIDC
- **Stable frontend interface**: `useAuth()` hook works the same regardless of provider
- **Board-scoped RBAC**: Role-based access control with `owner`, `editor`, `viewer` roles
- **Multi-tenancy**: Support for multiple tenants with isolated data
- **JIT provisioning**: Users auto-created on first login from any provider
- **SSR-friendly**: Token management works in both client and server environments

## Architecture Overview

```mermaid
graph TB
    Frontend[Frontend App]
    Hook[useAuth Hook]
    Provider[Auth Provider]
    API[Backend API]
    Adapter[Auth Adapter]
    DB[Database]

    Frontend --> Hook
    Hook --> Provider
    Provider --> API
    API --> Adapter
    Adapter --> DB

    Provider -.->|JWT Token| API
    API -.->|User Context| Frontend
```

### Backend Components

- **AuthAdapter Interface**: Provider-agnostic token verification
- **AuthContext**: Runtime authentication context for requests
- **Middleware**: Extracts tokens, verifies with adapters, provides context
- **JIT Provisioning**: Auto-creates local users from external identities
- **RBAC System**: Board-scoped permissions with helper functions

### Frontend Components

- **useAuth Hook**: Stable interface regardless of auth provider
- **Auth Providers**: Provider-specific implementations (JWT, Supabase, etc.)
- **GraphQL Client**: Automatic token injection via urql exchanges
- **Context System**: React context for auth state management

## Quick Start

### 1. Choose Your Auth Provider

For development, use the built-in `NoAuthProvider`:

```typescript
// No Auth (development only - included in core package)
import { NoAuthProvider } from "@weirdfingers/boards";
const authProvider = new NoAuthProvider();
```

**Production Auth Providers** (coming soon):
- JWT (self-managed)
- Supabase
- Clerk
- Auth0

Until production providers are available, you can implement custom auth by extending the `BaseAuthProvider` class.

### 2. Set Up Your App

```typescript
import { AuthProvider, createGraphQLClient } from "@weirdfingers/boards";

function App() {
  const graphqlClient = createGraphQLClient({
    url: "http://localhost:8088/graphql",
    auth: authProvider,
    tenantId: "my-company",
  });

  return (
    <AuthProvider provider={authProvider}>
      <Provider value={graphqlClient}>
        <MyApp />
      </Provider>
    </AuthProvider>
  );
}
```

### 3. Use in Components

```typescript
import { useAuth } from "@weirdfingers/boards";

function MyComponent() {
  const { user, status, signIn, signOut } = useAuth();

  if (status === "loading") return <div>Loading...</div>;
  if (status === "unauthenticated") {
    return <button onClick={() => signIn()}>Sign In</button>;
  }

  return (
    <div>
      <p>Hello, {user?.displayName}!</p>
      <button onClick={signOut}>Sign Out</button>
    </div>
  );
}
```

## Configuration

### Backend Configuration

Set environment variables:

```bash
# Choose your auth provider (defaults to 'none' for development)
BOARDS_AUTH_PROVIDER=none  # or 'jwt', 'supabase', 'clerk', 'auth0'

# Provider-specific config
# For JWT:
BOARDS_JWT_SECRET=your-secret-key

# For Supabase:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# For no-auth (optional):
BOARDS_AUTH_CONFIG='{"default_user_id": "my-dev-user"}'
```

### Frontend Configuration

Install the core package which includes `NoAuthProvider` for development:

```bash
npm install @weirdfingers/boards
```

## Auth Provider Architecture

The auth system is designed to support pluggable providers in separate packages (coming soon). This approach will keep your bundle size minimal:

**Planned Provider Packages:**

| Package                       | Dependencies            | Status      |
| ----------------------------- | ----------------------- | ----------- |
| `@weirdfingers/boards`        | None                    | ✅ Available (includes NoAuthProvider) |
| `@weirdfingers/auth-jwt`      | None                    | 🚧 Planned  |
| `@weirdfingers/auth-supabase` | `@supabase/supabase-js` | 🚧 Planned  |
| `@weirdfingers/auth-clerk`    | `@clerk/clerk-js`       | 🚧 Planned  |
| `@weirdfingers/auth-auth0`    | `@auth0/auth0-spa-js`   | 🚧 Planned  |

**Benefits of this architecture:**

- 🌲 **Tree-shakable**: Only bundle what you use
- 📦 **Small bundles**: Core package is tiny
- 🔄 **Easy migration**: Swap providers without breaking changes
- 🛡️ **Type-safe**: Full TypeScript support
- 🔧 **Extensible**: Implement custom providers by extending `BaseAuthProvider`

## Next Steps

- **Getting Started**: [No Auth Setup](./providers/none.md) - Perfect for development
- **Production Setup**: [JWT](./providers/jwt.md) or [Supabase](./providers/supabase.md)
- [Authorization](./backend/authorization.md) - RBAC and permissions
- [Frontend Integration](./frontend/getting-started.md) - Frontend usage patterns
- [Backend Integration](./backend/auth-adapters.md) - Backend implementation details
