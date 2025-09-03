# No Authentication (Development Mode)

The no-auth provider allows you to run Boards without any authentication for local development. This is perfect for getting started quickly or working on features that don't require user management.

⚠️ **WARNING**: This mode should NEVER be used in production. All requests are treated as authenticated with a default user.

## Backend Setup

### Environment Variables

```bash
# No environment variables needed - this is the default!
# But you can explicitly set:
BOARDS_AUTH_PROVIDER=none
```

Or configure a custom development user:

```bash
BOARDS_AUTH_PROVIDER=none
BOARDS_AUTH_CONFIG='{"default_user_id": "my-dev-user", "default_tenant": "dev-tenant"}'
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `default_user_id` | `"dev-user"` | User ID for the development user |
| `default_tenant` | `"default"` | Tenant ID for development |

## Frontend Setup

### Installation

```bash
npm install @weirdfingers/boards-frontend
```

### Provider Configuration

```typescript
import { NoAuthProvider, AuthProvider } from '@weirdfingers/boards-frontend';

const authProvider = new NoAuthProvider({
  defaultUserId: 'dev-user',
  defaultEmail: 'dev@example.com',
  defaultDisplayName: 'Development User',
  tenantId: 'my-company', // optional
});

function App() {
  return (
    <AuthProvider provider={authProvider}>
      {/* Your app */}
    </AuthProvider>
  );
}
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `defaultUserId` | `"dev-user"` | User ID for development |
| `defaultEmail` | `"dev@example.com"` | Email for development user |
| `defaultDisplayName` | `"Development User"` | Display name for development user |
| `tenantId` | `undefined` | Tenant ID for multi-tenant apps |

## Usage

### No Authentication Required

With no-auth mode, your components work exactly the same as with real authentication:

```typescript
import { useAuth } from '@weirdfingers/boards-frontend';

function MyComponent() {
  const { user, status, signIn, signOut } = useAuth();

  // Status is always 'authenticated' in no-auth mode
  console.log(status); // 'authenticated'
  
  // User is always the configured development user
  console.log(user); // { id: 'dev-user', email: 'dev@example.com', ... }

  return (
    <div>
      <p>Hello, {user?.displayName}!</p>
      <p>Status: {status}</p>
      {/* These buttons work but don't do anything in no-auth mode */}
      <button onClick={() => signIn()}>Sign In (no-op)</button>
      <button onClick={signOut}>Sign Out (no-op)</button>
    </div>
  );
}
```

### API Requests

API requests work without authentication headers, but you can still send them:

```typescript
// This works without any token
fetch('/api/boards')

// This also works - any token is accepted
fetch('/api/boards', {
  headers: {
    'Authorization': 'Bearer anything-goes'
  }
})
```

### GraphQL Client

The GraphQL client automatically handles no-auth mode:

```typescript
import { createGraphQLClient, NoAuthProvider } from '@weirdfingers/boards-frontend';

const authProvider = new NoAuthProvider();

const client = createGraphQLClient({
  url: 'http://localhost:8000/graphql',
  auth: authProvider, // Will provide fake tokens
});

// All GraphQL operations work normally
const result = await client.query(GET_BOARDS).toPromise();
```

## Development Workflow

### Quick Start (No Configuration)

1. **Start your backend** - no environment variables needed
2. **Use NoAuthProvider** in your frontend
3. **Start developing** - authentication is completely bypassed

```typescript
// Absolute minimal setup
import { NoAuthProvider, AuthProvider } from '@weirdfingers/boards-frontend';

const authProvider = new NoAuthProvider();

function App() {
  return (
    <AuthProvider provider={authProvider}>
      <MyApp />
    </AuthProvider>
  );
}
```

### Migration to Real Auth

When you're ready to add real authentication:

1. **Change the provider**:
```typescript
// From this:
const authProvider = new NoAuthProvider();

// To this:
const authProvider = new JWTAuthProvider({
  apiUrl: process.env.NEXT_PUBLIC_API_URL!,
});
```

2. **Set environment variables**:
```bash
BOARDS_AUTH_PROVIDER=jwt
BOARDS_JWT_SECRET=your-secret-key
```

3. **No code changes needed** - your components continue working!

## Console Warnings

You'll see warning messages to remind you that no-auth is active:

**Backend Console:**
```
WARNING:boards.auth.adapters.none:NoAuthAdapter is active - ALL requests will be treated as authenticated! This should ONLY be used in development.
```

**Frontend Console:**
```
🚨 NoAuthProvider is active - authentication is disabled! This should ONLY be used in development environments.
```

These warnings are intentional to prevent accidental production deployment.

## What Happens Behind the Scenes

### Backend Behavior

- **All requests** are treated as authenticated
- **Any token** (or no token) is accepted
- **Default user** is created: `dev-user` with email `dev@example.com`
- **JIT provisioning** still works - the dev user is created in your database
- **Authorization** still applies - the dev user needs board permissions

### Frontend Behavior

- **Always authenticated** - status is never 'unauthenticated'
- **signIn/signOut** are no-ops but safe to call
- **getToken()** returns a fake token: `"dev-token|no-auth-mode|always-valid"`
- **User object** is always the configured development user

### Database State

The development user is created in your database just like a real user:

```sql
-- This user will be created automatically
INSERT INTO users (
  id, tenant_id, auth_provider, auth_subject, 
  email, display_name
) VALUES (
  '...', 'default', 'none', 'dev-user',
  'dev@example.com', 'Development User'
);
```

## Testing Different Users

You can test with different development users by configuring multiple instances:

```typescript
// Different development users
const adminUser = new NoAuthProvider({
  defaultUserId: 'dev-admin',
  defaultEmail: 'admin@example.com',
  defaultDisplayName: 'Admin User',
});

const regularUser = new NoAuthProvider({
  defaultUserId: 'dev-user',
  defaultEmail: 'user@example.com', 
  defaultDisplayName: 'Regular User',
});

// Switch between them as needed
const authProvider = process.env.NODE_ENV === 'development' ? adminUser : regularUser;
```

## Security Reminders

### ⚠️ Never Deploy to Production

- **CI/CD pipelines** should fail if `BOARDS_AUTH_PROVIDER=none` in production
- **Environment validation** should reject no-auth mode in non-dev environments
- **Monitoring** should alert if no-auth mode is detected

### Example CI Check

```yaml
# .github/workflows/deploy.yml
- name: Validate auth configuration
  run: |
    if [ "$BOARDS_AUTH_PROVIDER" = "none" ] && [ "$ENVIRONMENT" = "production" ]; then
      echo "ERROR: No-auth mode cannot be used in production!"
      exit 1
    fi
```

## Troubleshooting

### "Permission Denied" Errors

Even in no-auth mode, you need board permissions:

```python
# Create board membership for dev user
await add_board_member(db, board_id, "dev-user", "owner")
```

### Database Not Found

Make sure your database is running and the development user can be created:

```bash
# Start your database
make docker-up

# Check if the user was created
SELECT * FROM users WHERE auth_provider = 'none';
```

### Multiple Dev Users

If you need different permissions, create multiple boards with different owners:

```python
# Board owned by dev-admin
board1 = await create_board(owner_id="dev-admin") 

# Board owned by dev-user  
board2 = await create_board(owner_id="dev-user")
```