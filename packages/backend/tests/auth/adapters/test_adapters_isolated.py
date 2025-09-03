"""Isolated tests for auth adapters (no middleware dependencies)."""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Import adapters directly to avoid middleware imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from boards.auth.adapters.jwt import JWTAuthAdapter
from boards.auth.adapters.none import NoAuthAdapter
from boards.auth.adapters.base import AuthenticationError


class TestJWTAdapterIsolated:
    """Test JWT authentication adapter in isolation."""
    
    @pytest.fixture
    def secret_key(self):
        return "test-secret-key-for-testing-only"

    @pytest.fixture
    def jwt_adapter(self, secret_key):
        return JWTAuthAdapter(
            secret_key=secret_key,
            algorithm="HS256",
            issuer="test-boards",
            audience="test-api"
        )

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
        claims = {"role": "admin", "org": "test-org"}
        
        # Issue a token
        token = await jwt_adapter.issue_token(user_id=user_id, claims=claims)
        assert token is not None
        assert isinstance(token, str)
        
        # Verify the issued token
        principal = await jwt_adapter.verify_token(token)
        assert principal["subject"] == str(user_id)
        assert principal["claims"]["role"] == "admin"
        assert principal["claims"]["org"] == "test-org"

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, jwt_adapter):
        """Test handling of malformed tokens."""
        with pytest.raises(AuthenticationError):
            await jwt_adapter.verify_token("not.a.jwt")

    @pytest.mark.asyncio 
    async def test_missing_subject_claim(self, jwt_adapter, secret_key):
        """Test token without subject fails."""
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "test-boards",
            "aud": "test-api",
            # Missing 'sub' claim
            "email": "test@example.com",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        with pytest.raises(AuthenticationError, match="Missing 'sub' claim"):
            await jwt_adapter.verify_token(token)


class TestNoAuthAdapterIsolated:
    """Test NoAuth authentication adapter in isolation."""
    
    @pytest.fixture
    def none_adapter(self):
        return NoAuthAdapter(
            default_user_id="test-dev-user",
            default_tenant="test-tenant"
        )

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

    @pytest.mark.asyncio
    async def test_get_user_info(self, none_adapter):
        """Test getting fake user info."""
        user_info = await none_adapter.get_user_info("any-token")
        
        assert user_info["id"] == "test-dev-user"
        assert user_info["mode"] == "no-auth"

    def test_default_configuration(self):
        """Test default adapter configuration."""
        adapter = NoAuthAdapter()
        
        assert adapter.default_user_id == "dev-user"
        assert adapter.default_tenant == "default"

    @pytest.mark.asyncio
    async def test_consistent_responses(self, none_adapter):
        """Test that same token always returns same principal."""
        token = "consistent-test-token"
        
        principal1 = await none_adapter.verify_token(token)
        principal2 = await none_adapter.verify_token(token)
        
        assert principal1 == principal2