# JWT Authentication

The JWT authentication provider allows you to use self-issued JSON Web Tokens for authentication. This is ideal when you want full control over your authentication flow.

## Backend Setup

### Environment Variables

```bash
BOARDS_AUTH_PROVIDER=jwt
BOARDS_JWT_SECRET=your-very-secure-secret-key-here
```

Or configure via JSON:

```bash
BOARDS_AUTH_PROVIDER=jwt
BOARDS_AUTH_CONFIG='{"secret_key": "your-secret", "algorithm": "HS256", "issuer": "my-app"}'
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `secret_key` | Required | Secret key for JWT signing/verification |
| `algorithm` | `"HS256"` | JWT signing algorithm |
| `issuer` | `"boards"` | JWT issuer claim |
| `audience` | `"boards-api"` | JWT audience claim |

## Frontend Setup

### Installation

```bash
npm install @weirdfingers/boards-frontend
```

### Provider Configuration

```typescript
import { JWTAuthProvider, AuthProvider } from '@weirdfingers/boards-frontend';

const authProvider = new JWTAuthProvider({
  apiUrl: process.env.NEXT_PUBLIC_API_URL!,
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
| `apiUrl` | Required | Your backend API URL |
| `tenantId` | `undefined` | Tenant ID for multi-tenant apps |
| `tokenStorageKey` | `"boards_jwt_token"` | localStorage key for token |
| `userStorageKey` | `"boards_user_info"` | localStorage key for user data |

## Usage

### Sign In

The JWT provider expects your backend to have a login endpoint that returns a JWT token:

```typescript
import { useAuth } from '@weirdfingers/boards-frontend';

function LoginForm() {
  const { signIn, status } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    
    try {
      await signIn({
        email: formData.get('email'),
        password: formData.get('password'),
      });
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="email" type="email" required />
      <input name="password" type="password" required />
      <button type="submit" disabled={status === 'loading'}>
        Sign In
      </button>
    </form>
  );
}
```

### Backend Login Endpoint

You'll need to implement a login endpoint that validates credentials and returns a JWT:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from boards.auth import get_auth_adapter

router = APIRouter(prefix="/auth")

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Validate credentials (implement your logic)
    user = await validate_user_credentials(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Issue JWT token
    adapter = get_auth_adapter()
    token = await adapter.issue_token(
        user_id=user.id,
        claims={
            "email": user.email,
            "name": user.display_name,
        }
    )
    
    return LoginResponse(token=token)
```

## JWT Token Format

The JWT tokens should contain these standard claims:

```json
{
  "iss": "boards",           // Issuer
  "aud": "boards-api",       // Audience  
  "sub": "user-uuid",        // Subject (user ID)
  "iat": 1640995200,         // Issued at
  "exp": 1641081600,         // Expiration
  "email": "user@example.com", // Optional: user email
  "name": "John Doe",        // Optional: display name
  "picture": "https://...",  // Optional: avatar URL
}
```

## Token Management

### Automatic Refresh

JWT tokens are not automatically refreshed. You should:

1. Set appropriate expiration times (recommended: 24 hours)
2. Handle token expiration gracefully in your UI
3. Implement refresh token flow if needed

### Storage

- Tokens are stored in `localStorage` by default
- For SSR, consider implementing server-side token storage
- Sensitive apps should use `httpOnly` cookies instead

## Security Considerations

### Secret Key Management

- Use a cryptographically strong secret key (256+ bits)
- Store secrets in environment variables or secret management systems
- Rotate secrets regularly
- Use different secrets for different environments

### Token Security

- Use HTTPS in production to protect tokens in transit
- Consider short expiration times for sensitive applications
- Implement proper logout (clear tokens)
- Consider using `httpOnly` cookies for enhanced security

### Example Strong Secret Generation

```bash
# Generate a secure secret key
openssl rand -base64 64
```

## Troubleshooting

### Common Issues

**"Invalid token" errors:**
- Check that `BOARDS_JWT_SECRET` matches between client and server
- Verify token hasn't expired
- Ensure clock synchronization between services

**Token not persisting:**
- Check browser localStorage is enabled
- Verify `tokenStorageKey` configuration
- Check for browser privacy settings blocking storage

**Authentication loops:**
- Verify API endpoint returns proper JWT format
- Check network tab for authentication requests
- Ensure backend and frontend are using same secret

### Debug Mode

Enable debug logging:

```typescript
const authProvider = new JWTAuthProvider({
  apiUrl: process.env.NEXT_PUBLIC_API_URL!,
  debug: true, // Enable debug logging
});
```