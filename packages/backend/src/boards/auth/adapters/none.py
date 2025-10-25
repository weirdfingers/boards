"""No-auth adapter for local development without authentication."""

from __future__ import annotations

import os
from uuid import UUID

from ...logging import get_logger
from .base import AuthenticationError, Principal

logger = get_logger(__name__)


class NoAuthAdapter:
    """
    No-auth adapter that bypasses authentication for local development.

    This adapter treats any request as authenticated with a default test user.
    WARNING: Only use this in development environments!
    """

    def __init__(self, default_user_id: str = "dev-user", default_tenant: str = "default"):
        self.default_user_id = default_user_id
        self.default_tenant = default_tenant

        # Production safety checks
        environment = os.getenv("ENVIRONMENT", "").lower()
        if environment in ("production", "prod"):
            logger.error(
                "NoAuthAdapter detected in production environment! "
                "This is a security risk and should never be used in production.",
                environment=environment,
            )
            raise RuntimeError(
                "NoAuthAdapter cannot be used in production environments. "
                "Please configure a proper authentication provider."
            )

        # Check for production-like domains
        api_url = os.getenv("BOARDS_API_URL", "")
        if api_url and not any(
            domain in api_url for domain in ["localhost", "127.0.0.1", "dev.", "staging."]
        ):
            logger.warning(
                "NoAuthAdapter detected with production-like URL. "
                "Ensure this is intentional and not deployed to production.",
                api_url=api_url,
            )

        logger.warning(
            "NoAuthAdapter is active - ALL requests will be treated as authenticated! "
            "This should ONLY be used in development.",
            user_id=default_user_id,
            environment=os.getenv("ENVIRONMENT", "unknown"),
        )

    async def verify_token(self, token: str) -> Principal:
        """
        Always returns a default principal - no actual verification.

        Any non-empty token will be accepted. The token content doesn't matter.
        """
        if not token:
            raise AuthenticationError("Token required (even in no-auth mode)")

        # Return a default principal for development
        principal = Principal(
            provider="none",
            subject=self.default_user_id,
            email="dev@example.com",
            display_name="Development User",
            claims={
                "mode": "development",
                "token": token[:20] + "..." if len(token) > 20 else token,
            },
        )
        # avatar_url is NotRequired, so we can add it as None if needed for tests
        principal["avatar_url"] = ""
        return principal

    async def issue_token(self, user_id: UUID | None = None, claims: dict | None = None) -> str:
        """Issue a fake development token."""
        token_parts = [
            "dev-token",
            str(user_id) if user_id else self.default_user_id,
            "no-auth-mode",
        ]

        if claims:
            token_parts.extend(f"{k}={v}" for k, v in claims.items())

        return "|".join(token_parts)

    async def get_user_info(self, token: str) -> dict:
        """Return fake user info for development."""
        return {
            "id": self.default_user_id,
            "email": "dev@example.com",
            "name": "Development User",
            "mode": "no-auth",
            "token_preview": token[:20] + "..." if len(token) > 20 else token,
        }
