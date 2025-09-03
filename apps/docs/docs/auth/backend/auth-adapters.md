# Auth Adapters

Auth adapters provide a provider-agnostic interface for token verification on the backend. Each adapter implements the same `AuthAdapter` protocol, allowing you to switch between auth providers without changing your application code.

## Adapter Interface

All auth adapters implement the `AuthAdapter` protocol:

```python
from typing import Protocol
from uuid import UUID
from .base import Principal

class AuthAdapter(Protocol):
    async def verify_token(self, token: str) -> Principal:
        """Verify a token and return the authenticated principal."""
        ...
    
    async def issue_token(
        self, 
        user_id: UUID | None = None, 
        claims: dict | None = None
    ) -> str:
        """Issue a new token (optional - some providers handle this client-side)."""
        ...
```

## Available Adapters

### NoAuthAdapter (Development)

For local development without authentication:

```python
from boards.auth.adapters.none import NoAuthAdapter

# Any token will be accepted
adapter = NoAuthAdapter(
    default_user_id="dev-user",
    default_tenant="default"
)
```

**Configuration:**
```bash
BOARDS_AUTH_PROVIDER=none
BOARDS_AUTH_CONFIG='{"default_user_id": "my-dev-user"}'
```

### JWTAuthAdapter

For self-managed JWT tokens:

```python
from boards.auth.adapters.jwt import JWTAuthAdapter

adapter = JWTAuthAdapter(
    secret="your-secret-key",
    algorithm="HS256"
)
```

**Configuration:**
```bash
BOARDS_AUTH_PROVIDER=jwt
BOARDS_JWT_SECRET=your-secret-key
BOARDS_JWT_ALGORITHM=HS256  # Optional, defaults to HS256
```

### SupabaseAuthAdapter

For Supabase authentication:

```python
from boards.auth.adapters.supabase import SupabaseAuthAdapter

adapter = SupabaseAuthAdapter(
    url="https://your-project.supabase.co",
    service_role_key="your-service-role-key"
)
```

**Configuration:**
```bash
BOARDS_AUTH_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### ClerkAuthAdapter

For Clerk authentication:

```python
from boards.auth.adapters.clerk import ClerkAuthAdapter

adapter = ClerkAuthAdapter(
    secret_key="your-clerk-secret-key"
)
```

**Configuration:**
```bash
BOARDS_AUTH_PROVIDER=clerk
CLERK_SECRET_KEY=your-clerk-secret-key
```

### Auth0AuthAdapter

For Auth0 authentication:

```python
from boards.auth.adapters.auth0 import Auth0AuthAdapter

adapter = Auth0AuthAdapter(
    domain="your-tenant.auth0.com",
    audience="your-api-audience"
)
```

**Configuration:**
```bash
BOARDS_AUTH_PROVIDER=auth0
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=your-api-audience
```

## Principal Structure

All adapters return a `Principal` object with consistent structure:

```python
from typing import TypedDict, NotRequired, Literal

class Principal(TypedDict):
    provider: Literal['supabase', 'clerk', 'auth0', 'oidc', 'jwt', 'none']
    subject: str  # Unique user ID from auth provider
    email: NotRequired[str]
    display_name: NotRequired[str]  
    avatar_url: NotRequired[str]
    claims: NotRequired[dict]  # Provider-specific claims
```

## Using Adapters

Adapters are automatically configured based on environment variables:

```python
from boards.auth.factory import get_auth_adapter

# Gets the configured adapter
adapter = get_auth_adapter()

# Use in middleware
principal = await adapter.verify_token(token)
```

## Custom Adapters

You can create custom adapters by implementing the `AuthAdapter` protocol:

```python
from boards.auth.adapters.base import AuthAdapter, Principal, AuthenticationError

class CustomAuthAdapter:
    async def verify_token(self, token: str) -> Principal:
        # Your verification logic here
        if not self.is_valid(token):
            raise AuthenticationError("Invalid token")
            
        return Principal(
            provider="custom",
            subject="user-123",
            email="user@example.com"
        )
    
    async def issue_token(self, user_id=None, claims=None) -> str:
        # Your token issuance logic
        return "custom-token"
```

Then register it in your app:

```python
from boards.auth.factory import register_auth_adapter
from .my_adapter import CustomAuthAdapter

# Register your adapter
register_auth_adapter("custom", lambda config: CustomAuthAdapter(**config))

# Configure via environment
BOARDS_AUTH_PROVIDER=custom
BOARDS_AUTH_CONFIG='{"custom_option": "value"}'
```

## Error Handling

All adapters should raise `AuthenticationError` for auth failures:

```python
from boards.auth.adapters.base import AuthenticationError

try:
    principal = await adapter.verify_token(token)
except AuthenticationError as e:
    # Handle authentication failure
    return {"error": "Unauthorized", "message": str(e)}
```

## Testing

Test your adapters with the provided test utilities:

```python
import pytest
from boards.auth.adapters.jwt import JWTAuthAdapter
from boards.auth.adapters.base import AuthenticationError

@pytest.mark.asyncio
async def test_jwt_adapter():
    adapter = JWTAuthAdapter(secret="test-secret")
    
    # Test valid token
    token = await adapter.issue_token(claims={"sub": "user-123"})
    principal = await adapter.verify_token(token)
    
    assert principal["provider"] == "jwt"
    assert principal["subject"] == "user-123"
    
    # Test invalid token
    with pytest.raises(AuthenticationError):
        await adapter.verify_token("invalid-token")
```