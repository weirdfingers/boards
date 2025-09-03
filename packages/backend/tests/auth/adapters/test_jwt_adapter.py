"""Tests for JWT authentication adapter."""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from boards.auth.adapters.jwt import JWTAuthAdapter
from boards.auth.adapters.base import AuthenticationError


@pytest.fixture
def secret_key():
    return "test-secret-key-for-testing-only"


@pytest.fixture
def jwt_adapter(secret_key):
    return JWTAuthAdapter(
        secret_key=secret_key,
        algorithm="HS256",
        issuer="test-boards",
        audience="test-api"
    )


@pytest.fixture
def valid_token(secret_key):
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
    return jwt.encode(payload, secret_key, algorithm="HS256")


@pytest.fixture
def expired_token(secret_key):
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {
        "iss": "test-boards",
        "aud": "test-api",
        "sub": "test-user-123", 
        "email": "test@example.com",
        "iat": past_time,
        "nbf": past_time,
        "exp": past_time + timedelta(minutes=30),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


class TestJWTAdapter:
    """Test JWT authentication adapter."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, jwt_adapter, valid_token):
        """Test verifying a valid JWT token."""
        principal = await jwt_adapter.verify_token(valid_token)
        
        assert principal["provider"] == "jwt"
        assert principal["subject"] == "test-user-123"
        assert principal["email"] == "test@example.com"
        assert principal["display_name"] == "Test User"
        assert principal["avatar_url"] == "https://example.com/avatar.jpg"
        assert "claims" in principal

    @pytest.mark.asyncio
    async def test_verify_expired_token(self, jwt_adapter, expired_token):
        """Test verifying an expired JWT token fails."""
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await jwt_adapter.verify_token(expired_token)

    @pytest.mark.asyncio
    async def test_verify_invalid_signature(self, jwt_adapter):
        """Test verifying a token with invalid signature fails."""
        # Create token with different secret
        wrong_secret = "wrong-secret-key"
        payload = {
            "iss": "test-boards",
            "aud": "test-api",
            "sub": "test-user-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        invalid_token = jwt.encode(payload, wrong_secret, algorithm="HS256")
        
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await jwt_adapter.verify_token(invalid_token)

    @pytest.mark.asyncio
    async def test_verify_missing_subject(self, jwt_adapter, secret_key):
        """Test verifying a token without subject fails."""
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

    @pytest.mark.asyncio
    async def test_verify_wrong_issuer(self, secret_key):
        """Test verifying a token with wrong issuer fails."""
        adapter = JWTAuthAdapter(
            secret_key=secret_key,
            issuer="expected-issuer"
        )
        
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "wrong-issuer",
            "aud": "test-api",
            "sub": "test-user-123",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await adapter.verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_malformed_token(self, jwt_adapter):
        """Test verifying a malformed token fails."""
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await jwt_adapter.verify_token("not-a-jwt-token")

    @pytest.mark.asyncio
    async def test_issue_token(self, jwt_adapter):
        """Test issuing a new JWT token."""
        user_id = uuid4()
        claims = {"role": "admin", "org": "test-org"}
        
        token = await jwt_adapter.issue_token(user_id=user_id, claims=claims)
        
        # Verify the issued token
        principal = await jwt_adapter.verify_token(token)
        assert principal["subject"] == str(user_id)
        assert principal["claims"]["role"] == "admin"
        assert principal["claims"]["org"] == "test-org"

    @pytest.mark.asyncio
    async def test_issue_token_without_user_id(self, jwt_adapter):
        """Test issuing a token without user ID."""
        token = await jwt_adapter.issue_token(claims={"test": "value"})
        
        # Should still be valid but without subject
        # We'll need to modify the verify logic to handle this case
        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_get_user_info(self, jwt_adapter, valid_token):
        """Test getting user info from token."""
        user_info = await jwt_adapter.get_user_info(valid_token)
        
        assert user_info["sub"] == "test-user-123"
        assert user_info["email"] == "test@example.com"
        assert user_info["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_info_invalid_token(self, jwt_adapter):
        """Test getting user info from invalid token."""
        user_info = await jwt_adapter.get_user_info("invalid-token")
        assert user_info == {}

    def test_adapter_configuration(self):
        """Test adapter initialization with different configurations."""
        adapter = JWTAuthAdapter(
            secret_key="test-key",
            algorithm="HS512",
            issuer="custom-issuer",
            audience="custom-audience"
        )
        
        assert adapter.secret_key == "test-key"
        assert adapter.algorithm == "HS512"
        assert adapter.issuer == "custom-issuer"
        assert adapter.audience == "custom-audience"

    @pytest.mark.asyncio
    async def test_minimal_token_claims(self, secret_key):
        """Test token with only required claims."""
        adapter = JWTAuthAdapter(secret_key=secret_key)
        
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "boards",
            "aud": "boards-api",
            "sub": "minimal-user",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        principal = await adapter.verify_token(token)
        assert principal["provider"] == "jwt"
        assert principal["subject"] == "minimal-user"
        # Optional claims should not be present
        assert "email" not in principal
        assert "display_name" not in principal
        assert "avatar_url" not in principal