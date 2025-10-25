"""Clerk authentication adapter."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from ...logging import get_logger
from .base import AuthenticationError, Principal

logger = get_logger(__name__)


class ClerkAuthAdapter:
    """Clerk authentication adapter."""

    def __init__(self, secret_key: str, jwks_url: str | None = None):
        """
        Initialize Clerk adapter.

        Args:
            secret_key: Clerk secret key for API calls
            jwks_url: Optional JWKS URL for JWT verification (auto-discovered if not provided)
        """
        self.secret_key = secret_key
        self.jwks_url = jwks_url or "https://api.clerk.dev/v1/jwks"
        self._jwks_cache: dict[str, Any] = {}
        self._http_client = httpx.AsyncClient()

    async def verify_token(self, token: str) -> Principal:
        """Verify a Clerk JWT token and return the principal."""
        try:
            import jwt
            from jwt.exceptions import InvalidTokenError

            # Get JWKS for verification
            jwks = await self._get_jwks()

            # Decode JWT header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise AuthenticationError("Missing 'kid' in JWT header")

            # Find the matching key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    # Store the JWK - PyJWT handles conversion internally
                    key = jwk
                    break

            if not key:
                raise AuthenticationError(f"Unable to find key with kid: {kid}")

            # Verify and decode the token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                options={
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                },
            )

            # Extract required claims
            subject = payload.get("sub")
            if not subject:
                raise AuthenticationError("Missing 'sub' claim in token")

            # Build principal from Clerk claims
            principal = Principal(
                provider="clerk",
                subject=subject,
            )

            # Add optional claims
            if email := payload.get("email"):
                principal["email"] = email
            elif email_addresses := payload.get("email_addresses"):
                # Clerk sometimes uses email_addresses array
                if email_addresses and len(email_addresses) > 0:
                    principal["email"] = email_addresses[0].get("email_address")

            # Extract name information
            if first_name := payload.get("given_name"):
                last_name = payload.get("family_name", "")
                principal["display_name"] = f"{first_name} {last_name}".strip()
            elif name := payload.get("name"):
                principal["display_name"] = name

            if picture := payload.get("picture"):
                principal["avatar_url"] = picture

            # Store all claims for additional context
            principal["claims"] = payload

            return principal

        except ImportError as e:
            raise AuthenticationError("PyJWT is required for Clerk authentication") from e
        except InvalidTokenError as e:
            logger.warning(f"Clerk JWT token validation failed: {e}")
            raise AuthenticationError(f"Invalid token: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error verifying Clerk token: {e}")
            raise AuthenticationError("Token verification failed") from e

    async def issue_token(self, user_id: UUID | None = None, claims: dict | None = None) -> str:
        """
        Issue a new token via Clerk (not commonly used).

        Note: Clerk typically handles token issuance on the client side.
        This method is provided for completeness but may not be used in practice.
        """
        raise NotImplementedError("Token issuance should be handled by Clerk client libraries")

    async def get_user_info(self, token: str) -> dict:
        """Get additional user information from Clerk API."""
        try:
            # First verify the token to get the subject
            principal = await self.verify_token(token)
            user_id = principal["subject"]

            # Get additional user info from Clerk API
            response = await self._http_client.get(
                f"https://api.clerk.dev/v1/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {self.secret_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get Clerk user info: {response.status_code}")
                return {}

        except Exception as e:
            logger.warning(f"Failed to get Clerk user info: {e}")
            return {}

    async def _get_jwks(self) -> dict[str, Any]:
        """Get JWKS from Clerk for JWT verification."""
        try:
            # Check cache first
            if self._jwks_cache:
                return self._jwks_cache

            response = await self._http_client.get(self.jwks_url)
            response.raise_for_status()

            jwks = response.json()
            self._jwks_cache = jwks

            return jwks

        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Clerk: {e}")
            raise AuthenticationError("Unable to verify token - JWKS unavailable") from e

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http_client.aclose()
