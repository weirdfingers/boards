"""Generic OIDC authentication adapter."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import httpx
import jwt

from ...logging import get_logger
from .base import AuthenticationError, Principal

logger = get_logger(__name__)


class OIDCAdapter:
    """Generic OIDC authentication adapter."""

    def __init__(
        self,
        issuer: str,
        client_id: str,
        client_secret: str | None = None,
        audience: str | None = None,
        jwks_url: str | None = None,
        jwks_cache_ttl: int = 3600,  # 1 hour default TTL
    ):
        """
        Initialize OIDC adapter.

        Args:
            issuer: OIDC issuer URL (e.g., "https://accounts.google.com")
            client_id: OIDC client ID
            client_secret: Optional client secret for API calls
            audience: Optional audience/client_id for token validation
            jwks_url: Optional JWKS URL (auto-discovered if not provided)
            jwks_cache_ttl: JWKS cache TTL in seconds (default: 3600 = 1 hour)
        """
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience or client_id
        self.jwks_url = jwks_url
        self.jwks_cache_ttl = jwks_cache_ttl
        self._oidc_config: dict[str, Any] = {}
        # Cache structure: {"data": jwks_data, "expires_at": timestamp}
        self._jwks_cache: dict[str, Any] = {}
        self._http_client = httpx.AsyncClient()

    async def verify_token(self, token: str) -> Principal:
        """Verify an OIDC JWT token and return the principal."""
        try:
            # JWT library already imported
            from jwt.exceptions import InvalidTokenError

            # Get OIDC configuration and JWKS
            await self._ensure_oidc_config()
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
                    # Store the JWK - PyJWT handles RSA/EC conversion internally
                    key = jwk
                    break

            if not key:
                raise AuthenticationError(f"Unable to find key with kid: {kid}")

            # Determine algorithm from JWK
            alg = jwk.get("alg", "RS256")

            # Verify and decode the token
            payload = jwt.decode(
                token,
                key,
                algorithms=[alg],
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

            # Build principal from OIDC claims
            principal = Principal(
                provider="oidc",
                subject=subject,
            )

            # Add optional standard OIDC claims
            if email := payload.get("email"):
                principal["email"] = email

            # Extract name information
            if name := payload.get("name"):
                principal["display_name"] = name
            elif given_name := payload.get("given_name"):
                family_name = payload.get("family_name", "")
                principal["display_name"] = f"{given_name} {family_name}".strip()
            elif preferred_username := payload.get("preferred_username"):
                principal["display_name"] = preferred_username

            if picture := payload.get("picture"):
                principal["avatar_url"] = picture

            # Store all claims for additional context
            principal["claims"] = payload

            return principal

        except ImportError as e:
            raise AuthenticationError("PyJWT is required for OIDC authentication") from e
        except InvalidTokenError as e:
            logger.warning(f"OIDC JWT token validation failed: {e}")
            raise AuthenticationError(f"Invalid token: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error verifying OIDC token: {e}")
            raise AuthenticationError("Token verification failed") from e

    async def issue_token(self, user_id: UUID | None = None, claims: dict | None = None) -> str:
        """
        Issue a new token via OIDC provider (rarely supported).

        Most OIDC providers handle token issuance via client libraries.
        """
        raise NotImplementedError("Token issuance should be handled by OIDC client libraries")

    async def get_user_info(self, token: str) -> dict:
        """Get additional user information from OIDC userinfo endpoint."""
        try:
            await self._ensure_oidc_config()
            userinfo_endpoint = self._oidc_config.get("userinfo_endpoint")

            if not userinfo_endpoint:
                logger.warning("No userinfo_endpoint in OIDC configuration")
                return {}

            response = await self._http_client.get(
                userinfo_endpoint,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get OIDC user info: {response.status_code}")
                return {}

        except Exception as e:
            logger.warning(f"Failed to get OIDC user info: {e}")
            return {}

    async def _ensure_oidc_config(self) -> None:
        """Ensure OIDC discovery configuration is loaded."""
        if self._oidc_config:
            return

        try:
            # OIDC Discovery
            discovery_url = f"{self.issuer}/.well-known/openid_configuration"
            response = await self._http_client.get(discovery_url)
            response.raise_for_status()

            self._oidc_config = response.json()

            # Set JWKS URL if not provided
            if not self.jwks_url:
                self.jwks_url = self._oidc_config.get("jwks_uri")

            if not self.jwks_url:
                raise AuthenticationError("Unable to determine JWKS URL")

        except Exception as e:
            logger.error(f"Failed to load OIDC configuration: {e}")
            raise AuthenticationError("Unable to load OIDC configuration") from e

    async def _get_jwks(self) -> dict[str, Any]:
        """Get JWKS from OIDC provider for JWT verification with TTL caching."""
        try:
            # Ensure we have JWKS URL
            if not self.jwks_url:
                await self._ensure_oidc_config()

            current_time = time.time()

            # Check cache first with TTL
            if (
                self._jwks_cache
                and "data" in self._jwks_cache
                and "expires_at" in self._jwks_cache
                and current_time < self._jwks_cache["expires_at"]
            ):
                logger.debug(
                    "Returning cached JWKS",
                    cache_expires_in=int(self._jwks_cache["expires_at"] - current_time),
                )
                return self._jwks_cache["data"]

            # Cache expired or empty, fetch fresh JWKS
            if self._jwks_cache:
                logger.info(
                    "JWKS cache expired, fetching fresh data",
                    cache_age=int(
                        current_time
                        - (self._jwks_cache.get("expires_at", current_time) - self.jwks_cache_ttl)
                    ),
                )

            # Ensure jwks_url is available after config check
            if not self.jwks_url:
                raise AuthenticationError("JWKS URL not available after configuration")

            logger.debug("Fetching JWKS from provider", jwks_url=self.jwks_url)
            response = await self._http_client.get(self.jwks_url)
            response.raise_for_status()

            jwks = response.json()

            # Determine TTL from cache-control header or use default
            cache_ttl = self.jwks_cache_ttl
            cache_control = response.headers.get("cache-control", "")
            if "max-age=" in cache_control:
                try:
                    # Extract max-age value from cache-control header
                    max_age_str = cache_control.split("max-age=")[1].split(",")[0].split(";")[0]
                    header_ttl = int(max_age_str)
                    # Use the smaller of header TTL and configured TTL for security
                    cache_ttl = min(header_ttl, self.jwks_cache_ttl)
                    logger.debug(
                        "Using cache-control max-age",
                        header_ttl=header_ttl,
                        effective_ttl=cache_ttl,
                    )
                except (ValueError, IndexError):
                    logger.debug(
                        "Could not parse cache-control max-age, using default TTL",
                        default_ttl=cache_ttl,
                    )

            # Update cache with TTL
            expires_at = current_time + cache_ttl
            self._jwks_cache = {"data": jwks, "expires_at": expires_at}

            logger.info(
                "Updated JWKS cache",
                cache_ttl=cache_ttl,
                expires_at=int(expires_at),
                keys_count=len(jwks.get("keys", [])),
            )

            return jwks

        except Exception as e:
            logger.error("Failed to fetch JWKS from OIDC provider", error=str(e))
            raise AuthenticationError("Unable to verify token - JWKS unavailable") from e

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http_client.aclose()
