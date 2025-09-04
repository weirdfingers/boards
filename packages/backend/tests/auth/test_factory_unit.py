"""Unit tests for auth adapter factory."""

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

    @patch.dict(os.environ, {
        "BOARDS_AUTH_PROVIDER": "jwt",
        "BOARDS_JWT_SECRET": "test-secret"
    })
    def test_jwt_adapter_with_env_vars(self):
        """Test creating JWT adapter with environment variables."""
        adapter = get_auth_adapter()
        assert isinstance(adapter, JWTAuthAdapter)
        assert adapter.secret_key == "test-secret"

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "jwt"})
    def test_jwt_adapter_missing_secret(self):
        """Test JWT adapter fails without secret key."""
        with pytest.raises(ValueError, match="JWT secret key is required"):
            get_auth_adapter()

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "unsupported"})
    def test_unsupported_provider(self):
        """Test unsupported provider raises error."""
        with pytest.raises(ValueError, match="Unsupported auth provider: unsupported"):
            get_auth_adapter()
