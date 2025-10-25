"""Base authentication adapter interface and types."""

from __future__ import annotations

from typing import Literal, NotRequired, Protocol, TypedDict
from uuid import UUID


class Principal(TypedDict):
    """Identity extracted from an incoming token."""

    provider: Literal["supabase", "clerk", "auth0", "oidc", "jwt", "none"]
    subject: str  # provider user id (sub)
    email: NotRequired[str]
    display_name: NotRequired[str]
    avatar_url: NotRequired[str]
    claims: NotRequired[dict]


class AuthAdapter(Protocol):
    """Provider-agnostic authentication adapter interface."""

    async def verify_token(self, token: str) -> Principal:
        """
        Verify a token and return the principal identity.

        Args:
            token: The authentication token to verify

        Returns:
            Principal containing identity information

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        ...

    async def issue_token(self, user_id: UUID | None = None, claims: dict | None = None) -> str:
        """
        Issue a new token (optional - not all providers support this).

        Args:
            user_id: Optional user ID to include in token
            claims: Optional additional claims to include

        Returns:
            Signed token string
        """
        ...

    async def get_user_info(self, token: str) -> dict:
        """
        Get provider-specific user information (optional enrichment).

        Args:
            token: Valid authentication token

        Returns:
            Dictionary of provider-specific user data
        """
        ...


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class AuthorizationError(Exception):
    """Raised when authorization fails."""

    pass
