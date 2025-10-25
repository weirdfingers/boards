# Frontend Getting Started

The Boards frontend auth system provides a stable, provider-agnostic interface through the `useAuth()` hook and pluggable auth providers. This guide shows you how to set up authentication in your React application.

## Installation

Install the core frontend package:

```bash
npm install @weirdfingers/boards
```

Then install your chosen auth provider package:

```bash
# For development (no auth)
# No additional package needed - NoAuthProvider included in core

# For JWT authentication
npm install @weirdfingers/auth-jwt

# For Supabase
npm install @weirdfingers/auth-supabase @supabase/supabase-js

# For Clerk
npm install @weirdfingers/auth-clerk @clerk/clerk-js

# For Auth0
npm install @weirdfingers/auth-auth0 @auth0/auth0-spa-js
```

## Basic Setup

### 1. Create Auth Provider

Choose and configure your auth provider:

```typescript
// No Auth (development only)
import { NoAuthProvider } from "@weirdfingers/boards";

const authProvider = new NoAuthProvider({
  apiUrl: "http://localhost:8088/api",
  tenantId: "default",
});
```

```typescript
// JWT (production)
import { JWTAuthProvider } from "@weirdfingers/auth-jwt";

const authProvider = new JWTAuthProvider({
  apiUrl: "http://localhost:8088/api",
  tenantId: "my-company",
  loginEndpoint: "/auth/login",
  signupEndpoint: "/auth/signup",
});
```

```typescript
// Supabase
import { SupabaseAuthProvider } from "@weirdfingers/auth-supabase";

const authProvider = new SupabaseAuthProvider({
  url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
  anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  tenantId: "my-company",
});
```

### 2. Wrap Your App

```typescript
import { AuthProvider, createGraphQLClient } from "@weirdfingers/boards";
import { Provider } from "urql";

function App() {
  // TODO(cleanup): if this is a functional component, then simply instantiating
  // a variable for the client isnt what we want to do. State, probably?
  // Create GraphQL client with auth integration
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

export default App;
```

### 3. Use in Components

```typescript
import { useAuth } from "@weirdfingers/boards";

function MyComponent() {
  const { user, status, signIn, signOut, signUp, refreshToken } = useAuth();

  // Show loading state
  if (status === "loading") {
    return <div>Loading...</div>;
  }

  // Show sign in form
  if (status === "unauthenticated") {
    return (
      <div>
        <button onClick={() => signIn()}>Sign In</button>
        <button onClick={() => signUp()}>Sign Up</button>
      </div>
    );
  }

  // Show authenticated content
  return (
    <div>
      <div>
        <img src={user.avatarUrl} alt="Avatar" />
        <h2>Hello, {user.displayName}!</h2>
        <p>{user.email}</p>
      </div>
      <button onClick={signOut}>Sign Out</button>
    </div>
  );
}
```

## useAuth Hook API

The `useAuth()` hook provides a consistent interface regardless of auth provider:

```typescript
interface AuthState {
  // Current user (null if not authenticated)
  user: User | null;

  // Authentication status
  status: "loading" | "authenticated" | "unauthenticated";

  // Authentication methods
  signIn: (credentials?: any) => Promise<void>;
  signOut: () => Promise<void>;
  signUp: (credentials?: any) => Promise<void>;

  // Token management
  refreshToken: () => Promise<void>;
  getToken: () => Promise<string | null>;
}

interface User {
  id: string;
  email?: string;
  displayName?: string;
  avatarUrl?: string;
  tenantId: string;
}
```

## GraphQL Integration

The auth system automatically handles GraphQL authentication:

```typescript
import { useQuery } from "urql";

function MyBoardsList() {
  // Token automatically included in requests
  const [result] = useQuery({
    query: `
      query GetMyBoards {
        boards {
          id
          name
          role  # Your role on this board
        }
      }
    `,
  });

  if (result.fetching) return <div>Loading...</div>;
  if (result.error) return <div>Error: {result.error.message}</div>;

  return (
    <ul>
      {result.data.boards.map((board) => (
        <li key={board.id}>
          {board.name} (Role: {board.role})
        </li>
      ))}
    </ul>
  );
}
```

## Error Handling

Handle auth errors gracefully:

```typescript
import { useAuth } from "@weirdfingers/boards";
import { useEffect, useState } from "react";

function SignInForm() {
  const { signIn } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleSignIn = async (email: string, password: string) => {
    try {
      setError(null);
      await signIn({ email, password });
    } catch (err) {
      setError(err.message || "Sign in failed");
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        handleSignIn(formData.get("email"), formData.get("password"));
      }}
    >
      <input name="email" type="email" required />
      <input name="password" type="password" required />
      <button type="submit">Sign In</button>

      {error && <div className="error">{error}</div>}
    </form>
  );
}
```

## SSR/SSG Support (Next.js)

The auth system works with server-side rendering:

```typescript
// pages/_app.tsx
import { AuthProvider, createGraphQLClient } from "@weirdfingers/boards";
import { Provider } from "urql";
import { useMemo } from "react";

function MyApp({ Component, pageProps }) {
  const authProvider = useMemo(() => createAuthProvider(), []);

  const graphqlClient = useMemo(
    () =>
      createGraphQLClient({
        url: process.env.NEXT_PUBLIC_API_URL + "/graphql",
        auth: authProvider,
        tenantId: process.env.NEXT_PUBLIC_TENANT_ID,
      }),
    [authProvider]
  );

  return (
    <AuthProvider provider={authProvider}>
      <Provider value={graphqlClient}>
        <Component {...pageProps} />
      </Provider>
    </AuthProvider>
  );
}
```

## Protected Routes

Create protected route components:

```typescript
import { useAuth } from "@weirdfingers/boards";
import { useRouter } from "next/router";
import { useEffect } from "react";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return <div>Loading...</div>;
  }

  if (status === "unauthenticated") {
    return null; // Redirecting...
  }

  return <>{children}</>;
}

// Usage
function DashboardPage() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
```

## Environment Variables

Configure your auth provider with environment variables:

```bash
# Next.js (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8088
NEXT_PUBLIC_TENANT_ID=my-company

# For Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# For Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...

# For Auth0
NEXT_PUBLIC_AUTH0_DOMAIN=your-tenant.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your-client-id
```

## Provider-Specific Setup

Each auth provider may have additional setup requirements:

- **[No Auth](../providers/none.md)** - Development setup
- **[JWT](../providers/jwt.md)** - Self-managed tokens
- **[Supabase](../providers/supabase.md)** - Supabase setup
- **Clerk** - Coming soon
- **Auth0** - Coming soon

## Troubleshooting

### Common Issues

1. **Token not included in requests**: Make sure you're using the GraphQL client created with `createGraphQLClient()`

2. **"Loading" state never resolves**: Check that your auth provider is properly configured and can reach the backend

3. **CORS errors**: Ensure your backend allows requests from your frontend domain

4. **Redirects not working in development**: Some providers require HTTPS even in development

### Debug Mode

Enable debug logging:

```typescript
const authProvider = new JWTAuthProvider({
  // ... config
  debug: true, // Enable debug logs
});
```

### Network Inspection

Check the Network tab in browser DevTools:

- Authentication requests should include `Authorization: Bearer <token>` header
- GraphQL requests should include `X-Tenant: <tenantId>` header
- Token refresh should happen automatically before expiry
