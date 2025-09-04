"""Unit tests for NoAuth authentication adapter."""

from uuid import uuid4

import pytest

from boards.auth.adapters.base import AuthenticationError
from boards.auth.adapters.none import NoAuthAdapter


@pytest.fixture
def none_adapter():
    return NoAuthAdapter(
        default_user_id="test-dev-user",
        default_tenant="test-tenant"
    )


class TestNoAuthAdapter:
    """Test NoAuth authentication adapter."""

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
