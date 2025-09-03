"""No-auth adapter for local development without authentication."""

from __future__ import annotations

import logging
from uuid import UUID

from .base import AuthAdapter, Principal, AuthenticationError

logger = logging.getLogger(__name__)


class NoAuthAdapter:
    """
    No-auth adapter that bypasses authentication for local development.
    
    This adapter treats any request as authenticated with a default test user.
    WARNING: Only use this in development environments!
    """
    
    def __init__(self, default_user_id: str = "dev-user", default_tenant: str = "default"):
        self.default_user_id = default_user_id
        self.default_tenant = default_tenant
        logger.warning(
            "NoAuthAdapter is active - ALL requests will be treated as authenticated! "
            "This should ONLY be used in development."
        )
    
    async def verify_token(self, token: str) -> Principal:
        """
        Always returns a default principal - no actual verification.
        
        Any non-empty token will be accepted. The token content doesn't matter.
        """
        if not token:
            raise AuthenticationError("Token required (even in no-auth mode)")
        
        # Return a default principal for development
        return Principal(
            provider="none",
            subject=self.default_user_id,
            email="dev@example.com",
            display_name="Development User",
            claims={
                "mode": "development",
                "token": token[:20] + "..." if len(token) > 20 else token,
            }
        )
    
    async def issue_token(
        self, 
        user_id: UUID | None = None, 
        claims: dict | None = None
    ) -> str:
        """Issue a fake development token."""
        token_parts = [
            "dev-token",
            str(user_id) if user_id else self.default_user_id,
            "no-auth-mode"
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