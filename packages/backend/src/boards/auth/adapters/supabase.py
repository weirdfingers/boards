"""Supabase authentication adapter."""

from __future__ import annotations

from uuid import UUID

import jwt
from supabase import Client, create_client

from ...logging import get_logger
from .base import AuthenticationError, Principal

logger = get_logger(__name__)


class SupabaseAuthAdapter:
    """Supabase authentication adapter."""

    def __init__(self, url: str, service_role_key: str):
        """
        Initialize Supabase adapter.

        Args:
            url: Supabase project URL
            service_role_key: Service role key for admin operations
        """
        self.url = url
        self.service_role_key = service_role_key
        self.client: Client = create_client(url, service_role_key)

    async def verify_token(self, token: str) -> Principal:
        """Verify a Supabase JWT token and return the principal."""
        try:
            # Get user info from Supabase auth
            user_response = self.client.auth.get_user(token)

            if not user_response or not user_response.user:
                raise AuthenticationError("Invalid or expired token")

            user = user_response.user

            # Build principal from Supabase user
            principal = Principal(
                provider="supabase",
                subject=user.id,
            )

            # Add optional user data
            if user.email:
                principal["email"] = user.email

            # Extract display name from user metadata
            if user.user_metadata:
                if display_name := user.user_metadata.get("display_name") or user.user_metadata.get(
                    "full_name"
                ):
                    principal["display_name"] = display_name
                if avatar_url := user.user_metadata.get("avatar_url"):
                    principal["avatar_url"] = avatar_url

            # Store raw claims for additional context
            try:
                # Decode JWT without verification to get all claims
                # (we already verified via Supabase API)
                decoded = jwt.decode(token, options={"verify_signature": False})
                principal["claims"] = decoded
            except Exception as e:
                logger.debug("Could not decode JWT claims", error=str(e))

            return principal

        except Exception as e:
            logger.warning("Supabase token validation failed", error=str(e))
            raise AuthenticationError(f"Invalid token: {e}") from e

    async def issue_token(self, user_id: UUID | None = None, claims: dict | None = None) -> str:
        """
        Issue a new token via Supabase (not commonly used).

        Note: Supabase typically handles token issuance on the client side.
        This method is provided for completeness but may not be used in practice.
        """
        # Supabase doesn't provide a direct server-side token issuance API
        # This would typically be done on the client side
        raise NotImplementedError("Token issuance should be handled by Supabase client libraries")

    async def get_user_info(self, token: str) -> dict:
        """Get additional user information from Supabase."""
        try:
            user_response = self.client.auth.get_user(token)

            if not user_response or not user_response.user:
                return {}

            user = user_response.user

            return {
                "id": user.id,
                "email": user.email,
                "email_confirmed_at": user.email_confirmed_at,
                "phone": user.phone,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "user_metadata": user.user_metadata,
                "app_metadata": user.app_metadata,
            }

        except Exception as e:
            logger.warning("Failed to get Supabase user info", error=str(e))
            return {}
