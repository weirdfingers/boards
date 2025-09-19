"""Authentication dependencies for API endpoints."""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from ..auth import AuthContext, get_auth_context, get_auth_context_optional

logger = logging.getLogger(__name__)


class AuthenticatedUser(BaseModel):
    """Represents an authenticated user."""
    user_id: str
    tenant_id: str
    email: str | None = None


async def get_current_user(
    auth_context: AuthContext = Depends(get_auth_context)
) -> AuthenticatedUser:
    """
    Get the current authenticated user from the auth context.
    
    Args:
        auth_context: Authentication context from middleware
    
    Returns:
        AuthenticatedUser object with user information
    
    Raises:
        HTTPException: If user is not authenticated
    """
    if not auth_context.is_authenticated or not auth_context.user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        user_id=str(auth_context.user_id),
        tenant_id=auth_context.tenant_id,
        email=auth_context.principal.get("email") if auth_context.principal else None,
    )


async def get_current_user_optional(
    auth_context: AuthContext = Depends(get_auth_context_optional)
) -> AuthenticatedUser | None:
    """
    Optional authentication - returns None if not authenticated.
    
    Use this for endpoints that can work both authenticated and unauthenticated,
    but may provide different functionality based on auth status.
    """
    if not auth_context.is_authenticated or not auth_context.user_id:
        return None

    return AuthenticatedUser(
        user_id=str(auth_context.user_id),
        tenant_id=auth_context.tenant_id,
        email=auth_context.principal.get("email") if auth_context.principal else None,
    )


# Legacy support - keep the old function names for backward compatibility
async def get_auth_context_dependency() -> AuthContext:
    """Get auth context directly (for advanced use cases)."""
    return await get_auth_context()
