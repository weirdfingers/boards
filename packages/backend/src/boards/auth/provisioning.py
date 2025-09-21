"""User provisioning and management."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dbmodels import Users
from ..logging import get_logger
from .adapters.base import Principal

logger = get_logger(__name__)


async def ensure_local_user(
    db: AsyncSession,
    tenant_id: str,
    principal: Principal
) -> UUID:
    """
    Ensure a local user exists for the given principal (JIT provisioning).

    This function creates a local user record if one doesn't exist for the
    given (tenant_id, auth_provider, auth_subject) combination.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        principal: Authenticated principal from auth provider

    Returns:
        UUID of the local user
    """
    provider = principal["provider"]
    subject = principal["subject"]

    # Convert tenant_id to UUID if it's a string
    if isinstance(tenant_id, str):
        try:
            tenant_uuid = UUID(tenant_id)
        except ValueError:
            # If tenant_id is not a valid UUID string, we might need to look it up
            # For now, generate a UUID from the string (this might not be ideal)
            import hashlib
            tenant_uuid = UUID(hashlib.md5(tenant_id.encode()).hexdigest()[:32])
    else:
        tenant_uuid = tenant_id

    # Try to find existing user
    stmt = select(Users).where(
        and_(
            Users.tenant_id == tenant_uuid,
            Users.auth_provider == provider,
            Users.auth_subject == subject,
        )
    )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Update user info if provided in principal
        updated = False

        email = principal.get("email")
        if email and user.email != email:
            user.email = email
            updated = True

        display_name = principal.get("display_name")
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            updated = True

        avatar_url = principal.get("avatar_url")
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            updated = True

        if updated:
            await db.commit()
            logger.info("Updated user info", user_id=str(user.id))

        return user.id

    # Create new user
    user = Users(
        tenant_id=tenant_uuid,
        auth_provider=provider,
        auth_subject=subject,
        email=principal.get("email"),
        display_name=principal.get("display_name"),
        avatar_url=principal.get("avatar_url"),
        metadata_={
            "created_via": "jit_provisioning",
            "provider_claims": principal.get("claims", {}),
        }
    )

    db.add(user)
    await db.commit()

    logger.info(
        "Created new user via JIT provisioning",
        user_id=str(user.id),
        tenant_id=tenant_id,
        provider=provider
    )

    return user.id


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Users | None:
    """Get a user by ID."""
    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_auth_info(
    db: AsyncSession,
    tenant_id: str,
    auth_provider: str,
    auth_subject: str
) -> Users | None:
    """Get a user by auth provider information."""
    # Convert tenant_id to UUID if it's a string
    if isinstance(tenant_id, str):
        try:
            tenant_uuid = UUID(tenant_id)
        except ValueError:
            import hashlib
            tenant_uuid = UUID(hashlib.md5(tenant_id.encode()).hexdigest()[:32])
    else:
        tenant_uuid = tenant_id

    stmt = select(Users).where(
        and_(
            Users.tenant_id == tenant_uuid,
            Users.auth_provider == auth_provider,
            Users.auth_subject == auth_subject,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
