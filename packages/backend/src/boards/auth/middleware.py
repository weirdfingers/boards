"""Authentication middleware for FastAPI."""

from __future__ import annotations

from uuid import UUID

from fastapi import Header, HTTPException

from ..database.connection import get_async_session
from ..database.seed_data import ensure_tenant
from ..logging import get_logger
from .adapters.base import AuthenticationError
from .context import DEFAULT_TENANT_UUID, AuthContext
from .factory import get_auth_adapter_cached
from .provisioning import ensure_local_user
from .tenant_extraction import extract_tenant_from_claims

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
    adapter = get_auth_adapter_cached()

    # Check if we're in no-auth mode
    is_no_auth_mode = hasattr(adapter, "default_user_id")  # NoAuthAdapter has this attribute

    # Handle unauthenticated requests
    if not authorization:
        if is_no_auth_mode:
            # In no-auth mode, create a default token
            authorization = "Bearer dev-token"
        else:
            # Use header tenant or default for unauthenticated requests
            tenant_slug = x_tenant or "default"
            tenant_uuid = await _resolve_tenant_uuid(tenant_slug)
            return AuthContext(
                user_id=None,
                tenant_id=tenant_uuid,
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

        # Extract tenant from JWT/OIDC claims with fallback to header
        tenant_slug = extract_tenant_from_claims(principal, fallback_tenant=x_tenant)

        logger.debug(
            "Tenant resolved for authenticated request",
            tenant_slug=tenant_slug,
            header_tenant=x_tenant,
            provider=principal.get("provider"),
            subject=principal.get("subject"),
        )

        # Resolve tenant slug to UUID and perform JIT user provisioning
        try:
            async with get_async_session() as db:
                # Ensure tenant exists and get its UUID
                tenant_uuid = await ensure_tenant(db, slug=tenant_slug)
                # Now provision the user with the tenant UUID
                user_id = await ensure_local_user(db, tenant_uuid, principal)

            logger.debug(
                "User provisioned and tenant resolved",
                user_id=str(user_id),
                tenant_uuid=str(tenant_uuid),
                tenant_slug=tenant_slug,
            )
        except Exception as db_error:
            # Database connection failed, use the same deterministic fallback
            logger.error(
                "Database connection failed, using fallback user ID generation",
                error=str(db_error),
                principal_provider=principal.get("provider"),
                principal_subject=principal.get("subject"),
            )

            import hashlib

            provider = principal.get("provider", "unknown")
            subject = principal.get("subject", "anonymous")
            stable_input = f"{provider}:{subject}:{tenant_slug}"
            user_id_hash = hashlib.sha256(stable_input.encode()).hexdigest()[:32]
            # Format hash as UUID: 8-4-4-4-12 pattern
            formatted_uuid = (
                f"{user_id_hash[:8]}-{user_id_hash[8:12]}-"
                f"{user_id_hash[12:16]}-{user_id_hash[16:20]}-"
                f"{user_id_hash[20:32]}"
            )
            from uuid import UUID

            user_id = UUID(formatted_uuid)

            # Also resolve tenant_uuid in this fallback path
            tenant_uuid = await _resolve_tenant_uuid(tenant_slug)

        return AuthContext(
            user_id=user_id,
            tenant_id=tenant_uuid,
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
        tenant_slug = x_tenant or "default"
        tenant_uuid = await _resolve_tenant_uuid(tenant_slug)
        return AuthContext(
            user_id=None,
            tenant_id=tenant_uuid,
            principal=None,
            token=None,
        )


async def _resolve_tenant_uuid(tenant_slug: str) -> UUID:
    """
    Resolve a tenant slug to its UUID.

    Falls back to DEFAULT_TENANT_UUID if:
    - Database lookup fails
    - Tenant doesn't exist
    - Running in single-tenant mode

    Args:
        tenant_slug: The tenant slug to resolve (e.g., "default", "acme-corp")

    Returns:
        UUID of the tenant, or DEFAULT_TENANT_UUID if resolution fails
    """
    try:
        from ..database.connection import get_async_session
        from ..database.seed_data import ensure_tenant

        async with get_async_session() as db:
            tenant_uuid = await ensure_tenant(db, slug=tenant_slug)
            logger.debug(
                "Resolved tenant slug to UUID",
                tenant_slug=tenant_slug,
                tenant_uuid=str(tenant_uuid),
            )
            return tenant_uuid
    except Exception as e:
        logger.warning(
            "Failed to resolve tenant UUID, using default",
            tenant_slug=tenant_slug,
            error=str(e),
            default_uuid=str(DEFAULT_TENANT_UUID),
        )
        return DEFAULT_TENANT_UUID
