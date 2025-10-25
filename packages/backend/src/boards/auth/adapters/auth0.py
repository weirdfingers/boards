"""Auth0 OIDC authentication adapter."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import jwt

from ...logging import get_logger
from .base import AuthenticationError, Principal

logger = get_logger(__name__)


class Auth0OIDCAdapter:
    """Auth0 OIDC authentication adapter."""

    def __init__(
        self,
        domain: str,
        audience: str,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        """
        Initialize Auth0 adapter.

        Args:
            domain: Auth0 domain (e.g., "myapp.us.auth0.com")
            audience: Auth0 API identifier/audience
            client_id: Optional client ID for API calls
            client_secret: Optional client secret for API calls
        """
        self.domain = domain
        self.audience = audience
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer = f"https://{domain}/"
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self._jwks_cache: dict[str, Any] = {}
        self._http_client = httpx.AsyncClient()

    async def verify_token(self, token: str) -> Principal:
        """Verify an Auth0 JWT token and return the principal."""
        try:
            # JWT library already imported
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
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            # Extract required claims
            subject = payload.get("sub")
            if not subject:
                raise AuthenticationError("Missing 'sub' claim in token")

            # Build principal from Auth0 claims
            principal = Principal(
                provider="auth0",
                subject=subject,
            )

            # Add optional claims
            if email := payload.get("email"):
                principal["email"] = email

            # Extract name information
            if name := payload.get("name"):
                principal["display_name"] = name
            elif given_name := payload.get("given_name"):
                family_name = payload.get("family_name", "")
                principal["display_name"] = f"{given_name} {family_name}".strip()
            elif nickname := payload.get("nickname"):
                principal["display_name"] = nickname

            if picture := payload.get("picture"):
                principal["avatar_url"] = picture

            # Store all claims for additional context
            principal["claims"] = payload

            return principal

        except ImportError as e:
            raise AuthenticationError("PyJWT is required for Auth0 authentication") from e
        except InvalidTokenError as e:
            logger.warning(f"Auth0 JWT token validation failed: {e}")
            raise AuthenticationError(f"Invalid token: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error verifying Auth0 token: {e}")
            raise AuthenticationError("Token verification failed") from e

    async def issue_token(self, user_id: UUID | None = None, claims: dict | None = None) -> str:
        """
        Issue a new token via Auth0 Management API (requires client credentials).

        This is rarely used as Auth0 typically handles token issuance via client libraries.
        """
        if not self.client_id or not self.client_secret:
            raise NotImplementedError("Token issuance requires client_id and client_secret")

        try:
            # Get management API access token first
            await self._get_management_token()

            # This would require implementing Auth0's Management API token creation
            # which is complex and rarely used. Most apps use client-side auth.
            raise NotImplementedError(
                "Server-side token issuance not commonly supported. "
                "Use Auth0 client libraries for authentication."
            )

        except Exception as e:
            logger.error(f"Failed to issue Auth0 token: {e}")
            raise AuthenticationError("Token issuance failed") from e

    async def get_user_info(self, token: str) -> dict:
        """Get additional user information from Auth0 userinfo endpoint."""
        try:
            response = await self._http_client.get(
                f"https://{self.domain}/userinfo",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get Auth0 user info: {response.status_code}")
                return {}

        except Exception as e:
            logger.warning(f"Failed to get Auth0 user info: {e}")
            return {}

    async def _get_jwks(self) -> dict[str, Any]:
        """Get JWKS from Auth0 for JWT verification."""
        try:
            # Check cache first (in production, implement TTL)
            if self._jwks_cache:
                return self._jwks_cache

            response = await self._http_client.get(self.jwks_url)
            response.raise_for_status()

            jwks = response.json()
            self._jwks_cache = jwks

            return jwks

        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Auth0: {e}")
            raise AuthenticationError("Unable to verify token - JWKS unavailable") from e

    async def _get_management_token(self) -> str:
        """Get Auth0 Management API access token."""
        try:
            response = await self._http_client.post(
                f"https://{self.domain}/oauth/token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "audience": f"https://{self.domain}/api/v2/",
                    "grant_type": "client_credentials",
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            data = response.json()

            return data["access_token"]

        except Exception as e:
            logger.error(f"Failed to get Auth0 management token: {e}")
            raise AuthenticationError("Unable to get management token") from e

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http_client.aclose()
