"""
Reusable seed data functions for database initialization.

This module provides functions to seed initial data into the database,
including tenants, users, and other setup-time functionality.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..dbmodels import Tenants
from ..logging import get_logger

logger = get_logger(__name__)


async def ensure_tenant(
    db: AsyncSession,
    *,
    tenant_id: UUID | None = None,
    name: str | None = None,
    slug: str | None = None,
    settings_dict: dict[str, Any] | None = None,
) -> UUID:
    """
    Ensure a tenant exists in the database.

    This function creates a tenant if it doesn't exist, or returns the
    existing tenant's ID if it does.

    Args:
        db: Database session
        tenant_id: UUID for the tenant (if None, auto-generated)
        name: Tenant name (defaults to env var or "Default Tenant")
        slug: Tenant slug (defaults to env var or "default")
        settings_dict: Optional tenant settings/metadata

    Returns:
        UUID of the tenant (existing or newly created)
    """
    # Use environment variables with fallbacks
    if name is None:
        name = os.getenv("BOARDS_TENANT_NAME", "Default Tenant")

    if slug is None:
        slug = os.getenv("BOARDS_TENANT_SLUG", settings.default_tenant_slug)

    if settings_dict is None:
        settings_dict = {}

    # Check if tenant already exists by slug
    stmt = select(Tenants).where(Tenants.slug == slug)
    result = await db.execute(stmt)
    existing_tenant = result.scalar_one_or_none()

    if existing_tenant:
        logger.debug(
            "Tenant already exists",
            tenant_id=str(existing_tenant.id),
            slug=slug,
            name=existing_tenant.name,
        )
        return existing_tenant.id

    # Create new tenant
    new_tenant = Tenants(
        name=name,
        slug=slug,
        settings=settings_dict,
    )

    # Set specific ID if provided
    if tenant_id:
        new_tenant.id = tenant_id

    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)

    logger.info(
        "Created new tenant",
        tenant_id=str(new_tenant.id),
        slug=slug,
        name=name,
    )

    return new_tenant.id


async def ensure_default_tenant(db: AsyncSession) -> UUID:
    """
    Ensure the default tenant exists for single-tenant or no-auth mode.

    This is a convenience function that uses environment variables
    or defaults to create/get the default tenant.

    Args:
        db: Database session

    Returns:
        UUID of the default tenant
    """
    return await ensure_tenant(db)


async def seed_initial_data(db: AsyncSession) -> None:
    """
    Seed all initial data required for the application.

    This function can be extended to seed additional data like:
    - Default provider configurations
    - Initial admin users
    - Sample boards or generations
    - Default credit allocations

    Args:
        db: Database session
    """
    logger.info("Starting database seeding")

    # Always ensure default tenant exists in non-multi-tenant mode
    if not settings.multi_tenant_mode:
        tenant_id = await ensure_default_tenant(db)
        logger.info("Ensured default tenant exists", tenant_id=str(tenant_id))

    # Add more seed operations here as needed
    # For example:
    # await ensure_default_providers(db, tenant_id)
    # await ensure_admin_user(db, tenant_id)

    logger.info("Database seeding completed")


async def seed_tenant_with_data(
    db: AsyncSession,
    *,
    tenant_name: str,
    tenant_slug: str,
    tenant_settings: dict[str, Any] | None = None,
    include_sample_data: bool = False,
) -> UUID:
    """
    Create a new tenant with optional sample data.

    This function is useful for:
    - Multi-tenant setup
    - Creating demo tenants
    - Testing different tenant configurations

    Args:
        db: Database session
        tenant_name: Display name for the tenant
        tenant_slug: Unique slug for the tenant
        tenant_settings: Optional tenant-specific settings
        include_sample_data: Whether to create sample boards/generations

    Returns:
        UUID of the created tenant
    """
    tenant_id = await ensure_tenant(
        db,
        name=tenant_name,
        slug=tenant_slug,
        settings_dict=tenant_settings,
    )

    if include_sample_data:
        # Future: Add sample boards, users, generations
        logger.info(
            "Would create sample data for tenant",
            tenant_id=str(tenant_id),
            note="Sample data creation not yet implemented",
        )

    return tenant_id
