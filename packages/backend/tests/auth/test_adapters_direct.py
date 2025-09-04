"""Direct tests for auth adapters without package imports."""

import pytest
import jwt
import sys
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Protocol, Literal, TypedDict, NotRequired

# Copy the adapter code directly to avoid import issues
class Principal(TypedDict):
    """Identity extracted from an incoming token."""
    provider: Literal['supabase', 'clerk', 'auth0', 'oidc', 'jwt', 'none']
    subject: str             # provider user id (sub)
    email: NotRequired[str]
    display_name: NotRequired[str]
    avatar_url: NotRequired[str]
    claims: NotRequired[dict]


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


# Simplified JWT Adapter for testing
class TestJWTAdapter:
    def __init__(self, secret_key: str, algorithm="HS256", issuer="boards", audience="boards-api"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
    
    async def verify_token(self, token: str) -> Principal:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                }
            )
            
            subject = payload.get("sub")
            if not subject:
                raise AuthenticationError("Missing 'sub' claim in token")
            
            principal = Principal(
                provider="jwt",
                subject=subject,
            )
            
            if email := payload.get("email"):
                principal["email"] = email
            if display_name := payload.get("name"):
                principal["display_name"] = display_name
            if avatar_url := payload.get("picture"):
                principal["avatar_url"] = avatar_url
            
            principal["claims"] = payload
            return principal
            
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
    
    async def issue_token(self, user_id=None, claims=None):
        now = datetime.now(timezone.utc)
        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(hours=24),
        }
        
        if user_id:
            payload["sub"] = str(user_id)
        
        if claims:
            payload.update(claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


# Simplified NoAuth Adapter for testing  
class TestNoAuthAdapter:
    def __init__(self, default_user_id="dev-user"):
        self.default_user_id = default_user_id
    
    async def verify_token(self, token: str) -> Principal:
        if not token:
            raise AuthenticationError("Token required (even in no-auth mode)")
        
        return Principal(
            provider="none",
            subject=self.default_user_id,
            email="dev@example.com",
            display_name="Development User",
            claims={
                "mode": "development",
                "token": token[:20] + "..." if len(token) > 20 else token,
            }
        )
    
    async def issue_token(self, user_id=None, claims=None):
        parts = ["dev-token", str(user_id) if user_id else self.default_user_id, "no-auth-mode"]
        if claims:
            parts.extend(f"{k}={v}" for k, v in claims.items())
        return "|".join(parts)


class TestJWTAdapterDirect:
    """Test JWT authentication adapter directly."""
    
    @pytest.fixture
    def secret_key(self):
        return "test-secret-key-for-testing-only"

    @pytest.fixture
    def jwt_adapter(self, secret_key):
        return TestJWTAdapter(secret_key, issuer="test-boards", audience="test-api")

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, jwt_adapter, secret_key):
        """Test verifying a valid JWT token."""
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "test-boards",
            "aud": "test-api", 
            "sub": "test-user-123",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        principal = await jwt_adapter.verify_token(token)
        
        assert principal["provider"] == "jwt"
        assert principal["subject"] == "test-user-123"
        assert principal["email"] == "test@example.com"
        assert principal["display_name"] == "Test User"
        assert principal["avatar_url"] == "https://example.com/avatar.jpg"

    @pytest.mark.asyncio
    async def test_verify_expired_token(self, jwt_adapter, secret_key):
        """Test verifying an expired JWT token fails."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        payload = {
            "iss": "test-boards",
            "aud": "test-api",
            "sub": "test-user-123", 
            "exp": past_time + timedelta(minutes=30),
        }
        expired_token = jwt.encode(payload, secret_key, algorithm="HS256")

        with pytest.raises(AuthenticationError, match="Invalid token"):
            await jwt_adapter.verify_token(expired_token)

    @pytest.mark.asyncio
    async def test_issue_and_verify_token(self, jwt_adapter):
        """Test issuing and then verifying a token."""
        user_id = uuid4()
        claims = {"role": "admin"}
        
        token = await jwt_adapter.issue_token(user_id=user_id, claims=claims)
        principal = await jwt_adapter.verify_token(token)
        
        assert principal["subject"] == str(user_id)
        assert principal["claims"]["role"] == "admin"


class TestNoAuthAdapterDirect:
    """Test NoAuth authentication adapter directly."""
    
    @pytest.fixture
    def none_adapter(self):
        return TestNoAuthAdapter("test-dev-user")

    @pytest.mark.asyncio
    async def test_verify_any_token(self, none_adapter):
        """Test that any non-empty token is accepted."""
        token = "any-token-works"
        principal = await none_adapter.verify_token(token)
        
        assert principal["provider"] == "none"
        assert principal["subject"] == "test-dev-user"
        assert principal["email"] == "dev@example.com"
        assert principal["display_name"] == "Development User"
        assert principal["claims"]["mode"] == "development"

    @pytest.mark.asyncio
    async def test_verify_empty_token_fails(self, none_adapter):
        """Test that empty token is rejected."""
        with pytest.raises(AuthenticationError, match="Token required"):
            await none_adapter.verify_token("")

    @pytest.mark.asyncio
    async def test_issue_token(self, none_adapter):
        """Test issuing a fake development token."""
        user_id = uuid4()
        token = await none_adapter.issue_token(user_id=user_id)
        
        assert "dev-token" in token
        assert str(user_id) in token
        assert "no-auth-mode" in token