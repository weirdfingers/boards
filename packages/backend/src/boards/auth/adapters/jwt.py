"""JWT authentication adapter for self-issued tokens."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from .base import AuthAdapter, Principal, AuthenticationError

logger = logging.getLogger(__name__)


class JWTAuthAdapter:
    """JWT authentication adapter for self-issued tokens."""
    
    def __init__(
        self, 
        secret_key: str, 
        algorithm: str = "HS256",
        issuer: str = "boards",
        audience: str = "boards-api"
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
    
    async def verify_token(self, token: str) -> Principal:
        """Verify a JWT token and return the principal."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                }
            )
            
            # Extract required claims
            subject = payload.get("sub")
            if not subject:
                raise AuthenticationError("Missing 'sub' claim in token")
            
            # Build principal from JWT claims
            principal = Principal(
                provider="jwt",
                subject=subject,
            )
            
            # Add optional claims
            if email := payload.get("email"):
                principal["email"] = email
            if display_name := payload.get("name"):
                principal["display_name"] = display_name
            if avatar_url := payload.get("picture"):
                principal["avatar_url"] = avatar_url
            
            # Store all claims for additional context
            principal["claims"] = payload
            
            return principal
            
        except AuthenticationError:
            # Re-raise our own authentication errors
            raise
        except InvalidTokenError as e:
            logger.warning(f"JWT token validation failed: {e}")
            raise AuthenticationError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error verifying JWT token: {e}")
            raise AuthenticationError("Token verification failed")
    
    async def issue_token(
        self, 
        user_id: UUID | None = None, 
        claims: dict | None = None
    ) -> str:
        """Issue a new JWT token."""
        now = datetime.now(timezone.utc)
        
        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(hours=24),  # 24 hour expiry
        }
        
        if user_id:
            payload["sub"] = str(user_id)
        
        if claims:
            payload.update(claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def get_user_info(self, token: str) -> dict:
        """Get user info from JWT claims."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_signature": False}  # Already verified in verify_token
            )
            return payload
        except Exception as e:
            logger.warning(f"Failed to decode JWT for user info: {e}")
            return {}