"""Authentication middleware for FastAPI."""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import Header, HTTPException

# from ..db import get_database  # TODO: Implement when db module is ready
from .adapters.base import AuthenticationError
from .context import AuthContext
from .factory import get_auth_adapter_cached
from .provisioning import ensure_local_user
from ..logging import get_logger

logger = get_logger(__name__)


async def get_auth_context(
    authorization: Optional[str] = Header(None),
    x_tenant: Optional[str] = Header(None, alias="X-Tenant"),
) -> AuthContext:
    """
    Extract authentication context from request headers.
    
    This function:
    1. Extracts Bearer token from Authorization header
    2. Verifies token using the configured auth adapter
    3. Resolves tenant (defaults to 'default' for single-tenant)
    4. Performs JIT user provisioning
    5. Returns AuthContext for the request
    
    For no-auth mode, any token (or "dev-token") will work.
    
    Args:
        authorization: Authorization header (Bearer token)
        x_tenant: Tenant identifier header
        
    Returns:
        AuthContext with user, tenant, and token info
    """
    tenant_id = x_tenant or "default"
    adapter = get_auth_adapter_cached()
    
    # Check if we're in no-auth mode
    is_no_auth_mode = hasattr(adapter, 'default_user_id')  # NoAuthAdapter has this attribute
    
    # Handle unauthenticated requests
    if not authorization:
        if is_no_auth_mode:
            # In no-auth mode, create a default token
            authorization = "Bearer dev-token"
        else:
            return AuthContext(
                user_id=None,
                tenant_id=tenant_id,
                principal=None,
                token=None,
            )
    
    # Extract Bearer token
    if not authorization.startswith("Bearer "):
        logger.warning("Invalid authorization format received")
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    if not token:
        logger.warning("Empty token provided")
        raise HTTPException(
            status_code=401,
            detail="Empty token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify token with auth adapter
        principal = await adapter.verify_token(token)
        
        # Get database session for JIT user provisioning
        try:
            from ..database.connection import get_async_session
            async with get_async_session() as db:
                user_id = await ensure_local_user(db, tenant_id, principal)
        except ImportError:
            # Database module not available, use fallback
            user_id = uuid4()
        
        return AuthContext(
            user_id=user_id,
            tenant_id=tenant_id,
            principal=principal,
            token=token,
        )
        
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_auth_context_optional(
    authorization: Optional[str] = Header(None),
    x_tenant: Optional[str] = Header(None, alias="X-Tenant"),
) -> AuthContext:
    """
    Optional authentication - returns unauthenticated context if no token.
    
    Use this for endpoints that work both authenticated and unauthenticated.
    """
    try:
        return await get_auth_context(authorization, x_tenant)
    except HTTPException:
        # Return unauthenticated context
        tenant_id = x_tenant or "default"
        return AuthContext(
            user_id=None,
            tenant_id=tenant_id,
            principal=None,
            token=None,
        )