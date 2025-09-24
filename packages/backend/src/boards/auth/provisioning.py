"""User provisioning and management."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dbmodels import Users
from ..logging import get_logger
from .adapters.base import Principal

logger = get_logger(__name__)

# Namespace UUID for deterministic tenant ID generation
# This ensures consistent UUIDs across different parts of the application
TENANT_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # Using DNS namespace UUID


async def ensure_local_user(
    db: AsyncSession, tenant_id: str, principal: Principal
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
            # Generate a deterministic UUID from the tenant_id string
            # using UUID5 with a namespace for consistency
            tenant_uuid = uuid.uuid5(TENANT_NAMESPACE, tenant_id)
            logger.debug("Generated UUID for non-UUID tenant_id",
                        original_tenant_id=tenant_id,
                        generated_uuid=str(tenant_uuid))
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
        # Update user info if provided in principal, but preserve existing non-empty values
        updated = False

        email = principal.get("email")
        if email and not user.email:  # Only update if current email is empty/None
            user.email = email
            updated = True

        display_name = principal.get("display_name")
        # Only update if current display_name is empty/None
        if display_name and not user.display_name:
            user.display_name = display_name
            updated = True

        avatar_url = principal.get("avatar_url")
        if avatar_url and not user.avatar_url:  # Only update if current avatar_url is empty/None
            user.avatar_url = avatar_url
            updated = True

        if updated:
            await db.commit()
            await db.refresh(user)
            logger.info("Updated user info (preserving existing values)", user_id=str(user.id))

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
        },
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "Created new user via JIT provisioning",
        user_id=str(user.id),
        tenant_id=tenant_id,
        provider=provider,
    )

    return user.id


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Users | None:
    """Get a user by ID."""
    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_auth_info(
    db: AsyncSession, tenant_id: str | UUID, auth_provider: str, auth_subject: str
) -> Users | None:
    """Get a user by auth provider information."""
    # Convert tenant_id to UUID if it's a string
    if isinstance(tenant_id, str):
        try:
            tenant_uuid = UUID(tenant_id)
        except ValueError:
            # Generate a deterministic UUID from the tenant_id string
            # using UUID5 with a namespace for consistency
            tenant_uuid = uuid.uuid5(TENANT_NAMESPACE, tenant_id)
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
