"""Unit tests for JWT authentication adapter (without database dependencies)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from boards.auth.adapters.base import AuthenticationError
from boards.auth.adapters.jwt import JWTAuthAdapter


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
    now = datetime.now(UTC)
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
    async def test_verify_expired_token(self, jwt_adapter, secret_key):
        """Test verifying an expired JWT token fails."""
        past_time = datetime.now(UTC) - timedelta(hours=2)
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
