"""Tests for auth adapter factory."""

import os
from unittest.mock import patch

import pytest

from boards.auth.adapters.jwt import JWTAuthAdapter
from boards.auth.adapters.none import NoAuthAdapter
from boards.auth.factory import get_auth_adapter


class TestAuthFactory:
    """Test auth adapter factory."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_none_adapter(self):
        """Test that none adapter is default when no env vars set."""
        adapter = get_auth_adapter()
        assert isinstance(adapter, NoAuthAdapter)

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "none"})
    def test_explicit_none_adapter(self):
        """Test creating none adapter explicitly."""
        adapter = get_auth_adapter()
        assert isinstance(adapter, NoAuthAdapter)

    @patch.dict(
        os.environ,
        {
            "BOARDS_AUTH_PROVIDER": "none",
            "BOARDS_AUTH_CONFIG": '{"default_user_id": "custom-user", "default_tenant": "custom"}',
        },
    )
    def test_none_adapter_with_config(self):
        """Test none adapter with JSON config."""
        adapter = get_auth_adapter()
        assert isinstance(adapter, NoAuthAdapter)
        assert adapter.default_user_id == "custom-user"
        assert adapter.default_tenant == "custom"

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "jwt", "BOARDS_JWT_SECRET": "test-secret"})
    def test_jwt_adapter_with_env_vars(self):
        """Test creating JWT adapter with environment variables."""
        adapter = get_auth_adapter()
        assert isinstance(adapter, JWTAuthAdapter)
        assert adapter.secret_key == "test-secret"

    @patch.dict(
        os.environ,
        {
            "BOARDS_AUTH_PROVIDER": "jwt",
            "BOARDS_AUTH_CONFIG": '{"secret_key": "config-secret", "algorithm": "HS512"}',
        },
    )
    def test_jwt_adapter_with_config(self):
        """Test creating JWT adapter with JSON config."""
        adapter = get_auth_adapter()
        assert isinstance(adapter, JWTAuthAdapter)
        assert adapter.secret_key == "config-secret"
        assert adapter.algorithm == "HS512"

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "jwt"})
    def test_jwt_adapter_missing_secret(self):
        """Test JWT adapter fails without secret key."""
        with pytest.raises(ValueError, match="JWT secret key is required"):
            get_auth_adapter()

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "supabase"})
    @patch("boards.auth.adapters.supabase.create_client")
    def test_supabase_adapter(self, mock_create_client):
        """Test creating Supabase adapter."""
        from boards import config
        from boards.auth.adapters.supabase import SupabaseAuthAdapter

        # Patch the settings attributes directly since settings is imported at module load time
        with patch.object(config.settings, "supabase_url", "https://test.supabase.co"):
            with patch.object(config.settings, "supabase_service_role_key", "test-key"):
                adapter = get_auth_adapter()
                assert isinstance(adapter, SupabaseAuthAdapter)
                # Verify create_client was called with correct args
                mock_create_client.assert_called_once_with("https://test.supabase.co", "test-key")

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "supabase"})
    def test_supabase_adapter_missing_config(self):
        """Test Supabase adapter fails without config."""
        with pytest.raises(ValueError, match="Supabase URL and service role key are required"):
            get_auth_adapter()

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "clerk", "CLERK_SECRET_KEY": "test-clerk-key"})
    def test_clerk_adapter(self):
        """Test creating Clerk adapter."""
        from boards.auth.adapters.clerk import ClerkAuthAdapter

        adapter = get_auth_adapter()
        assert isinstance(adapter, ClerkAuthAdapter)

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "clerk"})
    def test_clerk_adapter_missing_secret(self):
        """Test Clerk adapter fails without secret key."""
        with pytest.raises(ValueError, match="Clerk secret key is required"):
            get_auth_adapter()

    @patch.dict(
        os.environ,
        {
            "BOARDS_AUTH_PROVIDER": "auth0",
            "AUTH0_DOMAIN": "test.auth0.com",
            "AUTH0_AUDIENCE": "test-api",
        },
    )
    def test_auth0_adapter(self):
        """Test creating Auth0 adapter."""
        from boards.auth.adapters.auth0 import Auth0OIDCAdapter

        adapter = get_auth_adapter()
        assert isinstance(adapter, Auth0OIDCAdapter)

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "auth0"})
    def test_auth0_adapter_missing_config(self):
        """Test Auth0 adapter fails without domain and audience."""
        with pytest.raises(ValueError, match="Auth0 domain and audience are required"):
            get_auth_adapter()

    @patch.dict(
        os.environ,
        {
            "BOARDS_AUTH_PROVIDER": "oidc",
            "OIDC_ISSUER": "https://accounts.google.com",
            "OIDC_CLIENT_ID": "test-client-id",
        },
    )
    def test_oidc_adapter(self):
        """Test creating OIDC adapter."""
        from boards.auth.adapters.oidc import OIDCAdapter

        adapter = get_auth_adapter()
        assert isinstance(adapter, OIDCAdapter)

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "oidc"})
    def test_oidc_adapter_missing_config(self):
        """Test OIDC adapter fails without issuer and client_id."""
        with pytest.raises(ValueError, match="OIDC issuer and client_id are required"):
            get_auth_adapter()

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "unsupported"})
    def test_unsupported_provider(self):
        """Test unsupported provider raises error."""
        with pytest.raises(ValueError, match="Unsupported auth provider: unsupported"):
            get_auth_adapter()

    @patch.dict(
        os.environ,
        {
            "BOARDS_AUTH_PROVIDER": "jwt",
            "BOARDS_AUTH_CONFIG": "invalid-json",
            "BOARDS_JWT_SECRET": "test-secret",
        },
    )
    def test_invalid_json_config_fallback(self):
        """Test that invalid JSON config falls back to empty dict."""
        adapter = get_auth_adapter()
        assert isinstance(adapter, JWTAuthAdapter)
        # Should still work with env var fallback

    def test_fresh_adapter_instances(self):
        """Test that fresh adapter instances are created for thread safety."""
        from boards.auth.factory import get_auth_adapter_cached

        adapter1 = get_auth_adapter_cached()
        adapter2 = get_auth_adapter_cached()

        # Should be different instances for thread safety
        assert adapter1 is not adapter2
        # But should be the same type
        assert type(adapter1) is type(adapter2)
