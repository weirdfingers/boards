---
title: Authentication Setup
description: Configure authentication providers for production deployment.
sidebar_position: 7
---

# Authentication Setup

Configure authentication for your Boards deployment. This guide covers deployment-specific configuration; for detailed provider documentation, see the [Authentication section](/docs/auth/overview).

## Provider Overview

| Provider | Best For |
|----------|----------|
| **none** | Development only |
| **jwt** | Self-managed auth, custom identity providers |
| **supabase** | Full-stack Supabase deployments |
| **clerk** | Quick setup, hosted auth UI |
| **auth0** | Enterprise features, compliance |
| **oidc** | Generic OpenID Connect providers |

## Basic Configuration

Set the auth provider via environment variable:

```bash
BOARDS_AUTH_PROVIDER=jwt  # or supabase, clerk, auth0, oidc, none
```

## JWT Authentication

Self-managed JWT tokens. Use when you have your own identity provider or want full control.

### Configuration

```bash
# Required
BOARDS_AUTH_PROVIDER=jwt
BOARDS_JWT_SECRET=your-256-bit-secret-key-here

# Optional
BOARDS_JWT_ALGORITHM=HS256       # Default: HS256
BOARDS_JWT_ISSUER=https://auth.example.com  # Validate issuer claim
BOARDS_JWT_AUDIENCE=boards-api   # Validate audience claim
```

### Token Format

Boards expects JWT tokens with these claims:

```json
{
  "sub": "user-id",           // Required: User identifier
  "email": "user@example.com", // Optional: User email
  "name": "User Name",         // Optional: Display name
  "iat": 1704067200,          // Issued at
  "exp": 1704153600           // Expiration
}
```

### Generating Secrets

Generate a secure secret:

```bash
openssl rand -base64 32
```

### Frontend Integration

Your frontend obtains tokens from your identity provider and passes them to Boards:

```typescript
import { JWTAuthProvider } from "@weirdfingers/boards";

const authProvider = new JWTAuthProvider({
  getToken: async () => {
    // Get token from your identity provider
    return await myAuthService.getAccessToken();
  },
});
```

## Supabase Authentication

Integrates with Supabase Auth for seamless authentication.

### Configuration

```bash
BOARDS_AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # Backend only, never expose
SUPABASE_ANON_KEY=your-anon-key  # For frontend
```

### Supabase Setup

1. Create a Supabase project
2. Enable desired auth providers in **Authentication** > **Providers**
3. Get keys from **Settings** > **API**

### Frontend Integration

```typescript
import { createClient } from "@supabase/supabase-js";
import { SupabaseAuthProvider } from "@weirdfingers/boards";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

const authProvider = new SupabaseAuthProvider({ supabase });
```

See [Supabase Auth Provider](/docs/auth/providers/supabase) for detailed setup.

## Clerk Authentication

Hosted authentication with pre-built UI components.

### Configuration

```bash
BOARDS_AUTH_PROVIDER=clerk
CLERK_SECRET_KEY=sk_live_xxxxx  # Backend
CLERK_PUBLISHABLE_KEY=pk_live_xxxxx  # Frontend
```

### Clerk Setup

1. Create a Clerk application at [clerk.com](https://clerk.com)
2. Configure sign-in methods
3. Get API keys from dashboard

### Frontend Integration

```typescript
import { ClerkProvider, useAuth } from "@clerk/nextjs";
import { ClerkAuthProvider } from "@weirdfingers/boards";

function App() {
  return (
    <ClerkProvider>
      <BoardsApp />
    </ClerkProvider>
  );
}

function BoardsApp() {
  const { getToken } = useAuth();
  const authProvider = new ClerkAuthProvider({ getToken });
  // ...
}
```

## Auth0 Authentication

Enterprise-grade authentication with extensive compliance features.

### Configuration

```bash
BOARDS_AUTH_PROVIDER=auth0
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_AUDIENCE=https://boards-api  # Your API identifier
```

### Auth0 Setup

1. Create an Auth0 tenant
2. Create an API in **Applications** > **APIs**
3. Create an application for your frontend
4. Configure connections (social, database, etc.)

### Frontend Integration

```typescript
import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import { Auth0AuthProvider } from "@weirdfingers/boards";

function App() {
  return (
    <Auth0Provider
      domain="your-tenant.auth0.com"
      clientId="your-client-id"
      authorizationParams={{
        audience: "https://boards-api",
      }}
    >
      <BoardsApp />
    </Auth0Provider>
  );
}
```

## Generic OIDC

For any OpenID Connect compatible identity provider.

### Configuration

```bash
BOARDS_AUTH_PROVIDER=oidc
BOARDS_OIDC_ISSUER=https://identity.example.com
BOARDS_OIDC_CLIENT_ID=boards-api
BOARDS_OIDC_CLIENT_SECRET=your-client-secret  # Optional
BOARDS_OIDC_AUDIENCE=boards-api  # Optional
```

### Compatible Providers

- Keycloak
- Okta
- Google Workspace
- Azure AD
- Any OIDC-compliant provider

## No Authentication (Development)

For development only. Creates a default user for all requests.

```bash
BOARDS_AUTH_PROVIDER=none

# Optional: Configure default user
BOARDS_AUTH_CONFIG='{"default_user_id": "dev-user", "default_tenant_id": "dev-tenant"}'
```

:::danger
Never use `none` auth in production. All requests will be authenticated as the default user.
:::

## Multi-Tenancy

For multi-tenant deployments, configure tenant isolation:

```bash
BOARDS_MULTI_TENANT=true
```

Tenant ID is extracted from JWT claims or determined by the auth provider. See [Multi-Tenancy](/docs/auth/multi-tenant) for details.

## Security Checklist

- [ ] Auth provider is NOT `none` in production
- [ ] JWT secrets are at least 256 bits
- [ ] Service role keys are never exposed to frontend
- [ ] HTTPS is enabled for all auth traffic
- [ ] Token expiration is configured appropriately
- [ ] CORS origins are restricted to your domains

## Environment Variable Summary

| Variable | Providers | Description |
|----------|-----------|-------------|
| `BOARDS_AUTH_PROVIDER` | All | Provider selection |
| `BOARDS_JWT_SECRET` | jwt | JWT signing secret |
| `BOARDS_JWT_ALGORITHM` | jwt | Signing algorithm |
| `BOARDS_JWT_ISSUER` | jwt | Expected issuer |
| `SUPABASE_URL` | supabase | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | supabase | Service role key |
| `CLERK_SECRET_KEY` | clerk | Clerk secret key |
| `AUTH0_DOMAIN` | auth0 | Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | auth0 | Auth0 client ID |
| `AUTH0_CLIENT_SECRET` | auth0 | Auth0 client secret |
| `BOARDS_OIDC_ISSUER` | oidc | OIDC issuer URL |
| `BOARDS_OIDC_CLIENT_ID` | oidc | OIDC client ID |

## Next Steps

- [Auth Provider Details](/docs/auth/overview) - Complete auth documentation
- [Configuration Reference](./configuration.md) - All environment variables
- [Frontend Deployment](./frontend.md) - Deploy the web application
