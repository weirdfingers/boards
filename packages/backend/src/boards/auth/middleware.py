"""Authentication middleware for FastAPI."""

from __future__ import annotations

from fastapi import Header, HTTPException

from ..logging import get_logger

# from ..db import get_database  # TODO: Implement when db module is ready
from .adapters.base import AuthenticationError
from .context import AuthContext
from .factory import get_auth_adapter_cached
from .provisioning import ensure_local_user

logger = get_logger(__name__)


async def get_auth_context(
    authorization: str | None = Header(None),
    x_tenant: str | None = Header(None, alias="X-Tenant"),
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
    is_no_auth_mode = hasattr(
        adapter, "default_user_id"
    )  # NoAuthAdapter has this attribute

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
        except ImportError as e:
            # Database module not available, use deterministic fallback
            logger.warning(
                "Database connection not available, using fallback user ID generation",
                error=str(e),
                principal_provider=principal.get("provider"),
                principal_subject=principal.get("subject"),
                fallback_mode="deterministic_uuid"
            )

            # Create a deterministic UUID based on principal's subject and provider
            # This ensures the same user gets the same ID across requests
            import hashlib
            provider = principal.get('provider', 'unknown')
            subject = principal.get('subject', 'anonymous')
            stable_input = f"{provider}:{subject}:{tenant_id}"
            user_id_hash = hashlib.sha256(stable_input.encode()).hexdigest()[:32]
            # Create a valid UUID from the hash
            # Format hash as UUID: 8-4-4-4-12 pattern
            formatted_uuid = (
                f"{user_id_hash[:8]}-{user_id_hash[8:12]}-"
                f"{user_id_hash[12:16]}-{user_id_hash[16:20]}-"
                f"{user_id_hash[20:32]}"
            )
            from uuid import UUID
            user_id = UUID(formatted_uuid)

            logger.info(
                "Generated deterministic fallback user ID",
                user_id=str(user_id),
                tenant_id=tenant_id,
                provider=principal.get("provider")
            )
        except Exception as db_error:
            # Database connection failed, use the same deterministic fallback
            logger.error(
                "Database connection failed, using fallback user ID generation",
                error=str(db_error),
                principal_provider=principal.get("provider"),
                principal_subject=principal.get("subject")
            )

            import hashlib
            provider = principal.get('provider', 'unknown')
            subject = principal.get('subject', 'anonymous')
            stable_input = f"{provider}:{subject}:{tenant_id}"
            user_id_hash = hashlib.sha256(stable_input.encode()).hexdigest()[:32]
            # Format hash as UUID: 8-4-4-4-12 pattern
            formatted_uuid = (
                f"{user_id_hash[:8]}-{user_id_hash[8:12]}-"
                f"{user_id_hash[12:16]}-{user_id_hash[16:20]}-"
                f"{user_id_hash[20:32]}"
            )
            from uuid import UUID
            user_id = UUID(formatted_uuid)

        return AuthContext(
            user_id=user_id,
            tenant_id=tenant_id,
            principal=principal,
            token=token,
        )

    except AuthenticationError as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error("Unexpected authentication error", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_auth_context_optional(
    authorization: str | None = Header(None),
    x_tenant: str | None = Header(None, alias="X-Tenant"),
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
