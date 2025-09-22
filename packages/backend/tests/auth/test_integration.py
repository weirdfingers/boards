"""Integration tests for authentication system."""

import os
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from boards.auth import AuthContext, get_auth_context
from boards.auth.adapters.jwt import JWTAuthAdapter
from boards.auth.factory import get_auth_adapter_cached

# Mock FastAPI app for testing
app = FastAPI()


@app.get("/protected")
async def protected_endpoint(auth: AuthContext = Depends(get_auth_context)):
    """Test endpoint that requires authentication."""
    if not auth.is_authenticated:
        return {"error": "Not authenticated"}

    return {
        "user_id": str(auth.user_id),
        "tenant_id": auth.tenant_id,
        "provider": auth.provider,
        "authenticated": auth.is_authenticated,
    }


@app.get("/public")
async def public_endpoint(auth: AuthContext = Depends(get_auth_context)):
    """Test endpoint that works with or without auth."""
    return {
        "authenticated": auth.is_authenticated,
        "provider": auth.provider,
    }


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)




class TestAuthIntegration:
    """Integration tests for authentication system."""

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "none"})
    @patch("boards.auth.middleware.ensure_local_user")
    def test_none_auth_integration(self, mock_ensure_user, client):
        """Test end-to-end authentication with none adapter."""
        # Setup mocks
        mock_ensure_user.return_value = "test-user-uuid"

        # Note: Auth adapters are no longer cached for thread safety

        # Test unauthenticated request (no-auth should auto-authenticate)
        response = client.get("/protected")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["provider"] == "none"
        # User ID will be a randomly generated UUID since database isn't available in tests
        assert data["user_id"] is not None
        assert data["tenant_id"] == "default"

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "none"})
    @patch("boards.auth.middleware.ensure_local_user")
    def test_none_auth_with_explicit_token(self, mock_ensure_user, client):
        """Test none auth with explicit Bearer token."""
        # Setup mocks
        mock_ensure_user.return_value = "test-user-uuid"

        # Note: Auth adapters are no longer cached for thread safety

        # Test with Bearer token
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer any-token-works"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["provider"] == "none"

    @patch.dict(os.environ, {
        "BOARDS_AUTH_PROVIDER": "jwt",
        "BOARDS_JWT_SECRET": "test-secret-key"
    })
    @patch("boards.auth.middleware.ensure_local_user")
    def test_jwt_auth_integration(self, mock_ensure_user, client):
        """Test end-to-end authentication with JWT adapter."""
        # Setup mocks
        mock_ensure_user.return_value = "jwt-user-uuid"

        # Note: Auth adapters are no longer cached for thread safety

        # Create valid JWT token
        adapter = get_auth_adapter_cached()
        assert isinstance(adapter, JWTAuthAdapter)

        # Issue a token
        import asyncio
        from uuid import uuid4
        user_id = uuid4()
        token = asyncio.run(adapter.issue_token(
            user_id=user_id,
            claims={"email": "test@example.com", "name": "Test User"}
        ))

        # Test with valid JWT
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["provider"] == "jwt"
        # User ID will be a randomly generated UUID since database isn't available in tests
        assert data["user_id"] is not None

    @patch.dict(os.environ, {
        "BOARDS_AUTH_PROVIDER": "jwt",
        "BOARDS_JWT_SECRET": "test-secret-key"
    })
    def test_jwt_invalid_token(self, client):
        """Test JWT auth with invalid token."""
        # Note: Auth adapters are no longer cached for thread safety

        # Test with invalid JWT
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-jwt-token"}
        )

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "none"})
    @patch("boards.auth.middleware.ensure_local_user")
    def test_tenant_header(self, mock_ensure_user, client):
        """Test tenant header is processed correctly."""
        # Setup mocks
        mock_ensure_user.return_value = "test-user-uuid"

        # Note: Auth adapters are no longer cached for thread safety

        # Test with custom tenant
        response = client.get(
            "/protected",
            headers={
                "Authorization": "Bearer test-token",
                "X-Tenant": "custom-tenant"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "custom-tenant"

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "jwt", "BOARDS_JWT_SECRET": "test-secret"})
    def test_missing_authorization_header(self, client):
        """Test request without authorization header."""
        # Note: Auth adapters are no longer cached for thread safety

        # For public endpoint, should work
        response = client.get("/public")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["provider"] is None

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "jwt", "BOARDS_JWT_SECRET": "test-secret"})
    def test_invalid_authorization_format(self, client):
        """Test invalid authorization header format."""
        # Note: Auth adapters are no longer cached for thread safety

        response = client.get(
            "/protected",
            headers={"Authorization": "InvalidFormat token"}
        )

        assert response.status_code == 401
        assert "Invalid authorization format" in response.json()["detail"]

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "jwt", "BOARDS_JWT_SECRET": "test-secret"})
    def test_empty_token(self, client):
        """Test empty Bearer token."""
        # Note: Auth adapters are no longer cached for thread safety

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer "}
        )

        assert response.status_code == 401
        assert "Empty token" in response.json()["detail"]

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "none"})
    @patch("boards.auth.middleware.ensure_local_user")
    def test_jit_provisioning_called(self, mock_ensure_user, client):
        """Test that JIT provisioning is called correctly."""
        # Setup mocks - JIT provisioning is now called since database module is available
        from uuid import uuid4
        mock_user_id = uuid4()
        mock_ensure_user.return_value = mock_user_id

        # Note: Auth adapters are no longer cached for thread safety

        response = client.get("/protected")

        assert response.status_code == 200

        # JIT provisioning should now be called since database module is available
        mock_ensure_user.assert_called_once()

        # Verify the call arguments
        call_args = mock_ensure_user.call_args
        _, tenant_id, principal = call_args[0]

        assert tenant_id == "default"
        assert principal["provider"] == "none"
        assert principal["subject"] == "dev-user"
        assert principal["email"] == "dev@example.com"

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "unsupported"})
    def test_unsupported_provider_error(self, client):
        """Test that unsupported provider raises proper error."""
        # Note: Auth adapters are no longer cached for thread safety

        # This should fail when trying to get the adapter
        with pytest.raises(ValueError, match="Unsupported auth provider"):
            client.get("/protected")

    @patch.dict(os.environ, {"BOARDS_AUTH_PROVIDER": "none"})
    @patch("boards.auth.middleware.ensure_local_user")
    def test_database_error_handling(self, mock_ensure_user, client):
        """Test handling of database errors."""
        # Note: Auth adapters are no longer cached for thread safety

        # Setup mocks to raise error (though this test is less relevant now
        # since DB errors are caught by ImportError fallback)
        mock_ensure_user.side_effect = Exception("Database connection failed")

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer test-token"}
        )

        # Should succeed since we use fallback UUID when DB is not available
        assert response.status_code == 200
