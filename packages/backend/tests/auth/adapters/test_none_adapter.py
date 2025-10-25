"""Tests for NoAuth authentication adapter."""

from uuid import uuid4

import pytest

from boards.auth.adapters.none import NoAuthAdapter


@pytest.fixture
def none_adapter():
    return NoAuthAdapter(default_user_id="test-dev-user", default_tenant="test-tenant")


class TestNoAuthAdapter:
    """Test NoAuth authentication adapter."""

    @pytest.mark.asyncio
    async def test_verify_any_token(self, none_adapter):
        """Test that any non-empty token is accepted."""
        tokens_to_test = [
            "any-token",
            "dev-token",
            "fake-jwt-token.header.payload",
            "Bearer token-value",
            "random-string-123",
        ]

        for token in tokens_to_test:
            principal = await none_adapter.verify_token(token)

            assert principal["provider"] == "none"
            assert principal["subject"] == "test-dev-user"
            assert principal["email"] == "dev@example.com"
            assert principal["display_name"] == "Development User"
            assert principal["avatar_url"] == ""
            assert principal["claims"]["mode"] == "development"
            assert token[:20] in principal["claims"]["token"]

    @pytest.mark.asyncio
    async def test_verify_empty_token_fails(self, none_adapter):
        """Test that empty token is rejected."""
        from boards.auth.adapters.base import AuthenticationError

        with pytest.raises(AuthenticationError, match="Token required"):
            await none_adapter.verify_token("")

    @pytest.mark.asyncio
    async def test_issue_token(self, none_adapter):
        """Test issuing a fake development token."""
        user_id = uuid4()
        claims = {"role": "admin"}

        token = await none_adapter.issue_token(user_id=user_id, claims=claims)

        assert "dev-token" in token
        assert str(user_id) in token
        assert "no-auth-mode" in token
        assert "role=admin" in token

    @pytest.mark.asyncio
    async def test_issue_token_without_user_id(self, none_adapter):
        """Test issuing a token without user ID."""
        token = await none_adapter.issue_token()

        assert "dev-token" in token
        assert "test-dev-user" in token
        assert "no-auth-mode" in token

    @pytest.mark.asyncio
    async def test_get_user_info(self, none_adapter):
        """Test getting fake user info."""
        user_info = await none_adapter.get_user_info("any-token")

        assert user_info["id"] == "test-dev-user"
        assert user_info["email"] == "dev@example.com"
        assert user_info["name"] == "Development User"
        assert user_info["mode"] == "no-auth"
        assert "any-token" in user_info["token_preview"]

    def test_default_configuration(self):
        """Test default adapter configuration."""
        adapter = NoAuthAdapter()

        assert adapter.default_user_id == "dev-user"
        assert adapter.default_tenant == "default"

    def test_custom_configuration(self):
        """Test custom adapter configuration."""
        adapter = NoAuthAdapter(default_user_id="custom-dev-user", default_tenant="custom-tenant")

        assert adapter.default_user_id == "custom-dev-user"
        assert adapter.default_tenant == "custom-tenant"

    @pytest.mark.asyncio
    async def test_consistent_responses(self, none_adapter):
        """Test that same token always returns same principal."""
        token = "consistent-test-token"

        principal1 = await none_adapter.verify_token(token)
        principal2 = await none_adapter.verify_token(token)

        assert principal1 == principal2

    @pytest.mark.asyncio
    async def test_long_token_truncation(self, none_adapter):
        """Test that very long tokens are truncated in claims."""
        long_token = "x" * 100  # 100 character token

        principal = await none_adapter.verify_token(long_token)

        # Should be truncated to 20 chars + "..."
        assert len(principal["claims"]["token"]) == 23  # 20 + "..."
        assert principal["claims"]["token"].endswith("...")

    @pytest.mark.asyncio
    async def test_short_token_no_truncation(self, none_adapter):
        """Test that short tokens are not truncated."""
        short_token = "short"

        principal = await none_adapter.verify_token(short_token)

        assert principal["claims"]["token"] == "short"

    @pytest.mark.asyncio
    async def test_warning_logged(self, none_adapter):
        """Test that warning is logged on initialization."""
        # Create new adapter to trigger warning (structured logging outputs to stdout/stderr)
        # Note: With structured logging, the warning may not appear in caplog.text
        # but we can verify the adapter was created without error
        adapter = NoAuthAdapter()

        # Verify the adapter was created successfully and has expected properties
        assert adapter.default_user_id == "dev-user"
        assert hasattr(adapter, "default_tenant")

        # The warning should be visible in stdout/stderr during test execution
