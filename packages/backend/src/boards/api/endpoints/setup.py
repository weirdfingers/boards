"""
Setup endpoints for initial tenant configuration.

These endpoints help with one-time setup for single-tenant deployments
or initial configuration of multi-tenant environments.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update

from ...config import settings
from ...database.connection import get_async_session
from ...database.seed_data import ensure_tenant, seed_tenant_with_data
from ...dbmodels import Tenants
from ...logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class TenantSetupRequest(BaseModel):
    """Request model for tenant setup."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name for the tenant")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe slug for the tenant (lowercase, numbers, hyphens only)",
    )
    settings: dict[str, Any] = Field(
        default_factory=dict, description="Optional tenant-specific settings"
    )
    include_sample_data: bool = Field(
        default=False, description="Whether to include sample boards and data"
    )


class TenantUpdateRequest(BaseModel):
    """Request model for tenant updates."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Display name for the tenant",
    )
    slug: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe slug for the tenant (lowercase, numbers, hyphens only)",
    )
    settings: dict[str, Any] | None = Field(None, description="Tenant-specific settings")


class TenantResponse(BaseModel):
    """Response model for tenant operations."""

    tenant_id: str = Field(..., description="UUID of the tenant")
    name: str = Field(..., description="Display name of the tenant")
    slug: str = Field(..., description="Slug of the tenant")
    settings: dict[str, Any] = Field(..., description="Tenant-specific settings")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class TenantSetupResponse(BaseModel):
    """Response model for tenant setup."""

    tenant_id: str = Field(..., description="UUID of the created tenant")
    name: str = Field(..., description="Display name of the tenant")
    slug: str = Field(..., description="Slug of the tenant")
    message: str = Field(..., description="Success message")
    existing: bool = Field(..., description="Whether tenant already existed")


class TenantListResponse(BaseModel):
    """Response model for tenant list."""

    tenants: list[TenantResponse] = Field(..., description="List of tenants")
    total_count: int = Field(..., description="Total number of tenants")


@router.post("/tenant", response_model=TenantSetupResponse)
async def setup_tenant(request: TenantSetupRequest) -> TenantSetupResponse:
    """
    Create or configure a tenant for initial setup.

    This endpoint is useful for:
    - Single-tenant initial setup
    - Creating new tenants in multi-tenant mode
    - Demo/development tenant creation

    In single-tenant mode, this is typically called once during deployment.
    In multi-tenant mode, this can be used for admin tenant creation.
    """
    logger.info(
        "Setting up tenant",
        name=request.name,
        slug=request.slug,
        include_sample_data=request.include_sample_data,
    )

    try:
        async with get_async_session() as db:
            # Check if tenant already exists
            existing_tenant_id = await ensure_tenant(
                db,
                name=request.name,
                slug=request.slug,
                settings_dict=request.settings,
            )

            # For now, we'll consider it "existing" if the ensure_tenant call
            # found an existing tenant. We could enhance this by checking
            # if the tenant was created or updated.
            try:
                # Try to create with sample data if requested
                if request.include_sample_data:
                    tenant_id = await seed_tenant_with_data(
                        db,
                        tenant_name=request.name,
                        tenant_slug=request.slug,
                        tenant_settings=request.settings,
                        include_sample_data=True,
                    )
                    existing = False  # seed_tenant_with_data creates new tenant
                else:
                    tenant_id = existing_tenant_id
                    existing = True  # assume it existed (could be enhanced)

            except Exception as e:
                # If seeding fails, we still have the basic tenant
                logger.warning(
                    "Sample data creation failed, but tenant was created",
                    error=str(e),
                    tenant_id=str(existing_tenant_id),
                )
                tenant_id = existing_tenant_id
                existing = True

            logger.info(
                "Tenant setup completed",
                tenant_id=str(tenant_id),
                name=request.name,
                slug=request.slug,
                existing=existing,
            )

            return TenantSetupResponse(
                tenant_id=str(tenant_id),
                name=request.name,
                slug=request.slug,
                message=f"Tenant {'configured' if existing else 'created'} successfully",
                existing=existing,
            )

    except Exception as e:
        logger.error("Tenant setup failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to setup tenant: {str(e)}") from e


@router.get("/tenant/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID = Path(..., description="UUID of the tenant to retrieve"),
) -> TenantResponse:
    """
    Get a specific tenant by ID.

    This endpoint retrieves detailed information about a tenant including
    its settings, creation date, and other metadata.
    """
    logger.info("Retrieving tenant", tenant_id=str(tenant_id))

    try:
        async with get_async_session() as db:
            # Query for the tenant
            stmt = select(Tenants).where(Tenants.id == tenant_id)
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()

            if not tenant:
                raise HTTPException(status_code=404, detail=f"Tenant with ID {tenant_id} not found")

            logger.info(
                "Tenant retrieved successfully",
                tenant_id=str(tenant_id),
                slug=tenant.slug,
            )

            return TenantResponse(
                tenant_id=str(tenant.id),
                name=tenant.name,
                slug=tenant.slug,
                settings=tenant.settings or {},
                created_at=tenant.created_at.isoformat() if tenant.created_at else "",
                updated_at=tenant.updated_at.isoformat() if tenant.updated_at else "",
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("Failed to retrieve tenant", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tenant: {str(e)}") from e


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants() -> TenantListResponse:
    """
    List all tenants in the system.

    This endpoint is useful for:
    - Multi-tenant administration
    - Tenant discovery and management
    - System overview and monitoring
    """
    logger.info("Listing all tenants")

    try:
        async with get_async_session() as db:
            # Query for all tenants, ordered by creation date
            stmt = select(Tenants).order_by(Tenants.created_at.desc())
            result = await db.execute(stmt)
            tenants = result.scalars().all()

            tenant_responses = [
                TenantResponse(
                    tenant_id=str(tenant.id),
                    name=tenant.name,
                    slug=tenant.slug,
                    settings=tenant.settings or {},
                    created_at=(tenant.created_at.isoformat() if tenant.created_at else ""),
                    updated_at=(tenant.updated_at.isoformat() if tenant.updated_at else ""),
                )
                for tenant in tenants
            ]

            logger.info(
                "Tenants listed successfully",
                total_count=len(tenant_responses),
            )

            return TenantListResponse(
                tenants=tenant_responses,
                total_count=len(tenant_responses),
            )

    except Exception as e:
        logger.error("Failed to list tenants", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list tenants: {str(e)}") from e


@router.put("/tenant/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    request: TenantUpdateRequest,
    tenant_id: UUID = Path(..., description="UUID of the tenant to update"),
) -> TenantResponse:
    """
    Update a specific tenant.

    This endpoint allows updating tenant information including:
    - Display name
    - Slug (URL identifier)
    - Settings (JSON metadata)

    Only provided fields will be updated; others remain unchanged.
    """
    logger.info(
        "Updating tenant",
        tenant_id=str(tenant_id),
        name=request.name,
        slug=request.slug,
    )

    try:
        async with get_async_session() as db:
            # First, check if tenant exists
            stmt = select(Tenants).where(Tenants.id == tenant_id)
            result = await db.execute(stmt)
            existing_tenant = result.scalar_one_or_none()

            if not existing_tenant:
                raise HTTPException(status_code=404, detail=f"Tenant with ID {tenant_id} not found")

            # Check for slug conflicts if slug is being updated
            if request.slug and request.slug != existing_tenant.slug:
                slug_check = select(Tenants).where(
                    (Tenants.slug == request.slug) & (Tenants.id != tenant_id)
                )
                result = await db.execute(slug_check)
                if result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=409,
                        detail=f"A tenant with slug '{request.slug}' already exists",
                    )

            # Build update data - only include provided fields
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.slug is not None:
                update_data["slug"] = request.slug
            if request.settings is not None:
                update_data["settings"] = request.settings

            # Add updated_at timestamp
            from datetime import datetime

            update_data["updated_at"] = datetime.now(UTC)

            if update_data:
                # Perform the update
                stmt = update(Tenants).where(Tenants.id == tenant_id).values(**update_data)
                await db.execute(stmt)
                await db.commit()

            # Fetch the updated tenant
            stmt = select(Tenants).where(Tenants.id == tenant_id)
            result = await db.execute(stmt)
            updated_tenant = result.scalar_one()

            logger.info(
                "Tenant updated successfully",
                tenant_id=str(tenant_id),
                name=updated_tenant.name,
                slug=updated_tenant.slug,
            )

            return TenantResponse(
                tenant_id=str(updated_tenant.id),
                name=updated_tenant.name,
                slug=updated_tenant.slug,
                settings=updated_tenant.settings or {},
                created_at=(
                    updated_tenant.created_at.isoformat() if updated_tenant.created_at else ""
                ),
                updated_at=(
                    updated_tenant.updated_at.isoformat() if updated_tenant.updated_at else ""
                ),
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("Failed to update tenant", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update tenant: {str(e)}") from e


@router.delete("/tenant/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID = Path(..., description="UUID of the tenant to delete"),
) -> dict[str, Any]:
    """
    Delete a specific tenant.

    **WARNING**: This operation is destructive and will cascade delete all related data:
    - All users in this tenant
    - All boards and their content
    - All generations and media
    - All provider configurations
    - All credit transactions

    This operation cannot be undone. Use with extreme caution.
    """
    logger.warning(
        "Attempting to delete tenant - this is a destructive operation",
        tenant_id=str(tenant_id),
    )

    try:
        async with get_async_session() as db:
            # First, check if tenant exists and get its info for logging
            stmt = select(Tenants).where(Tenants.id == tenant_id)
            result = await db.execute(stmt)
            existing_tenant = result.scalar_one_or_none()

            if not existing_tenant:
                raise HTTPException(status_code=404, detail=f"Tenant with ID {tenant_id} not found")

            # Prevent deletion of default tenant in single-tenant mode
            if (
                not settings.multi_tenant_mode
                and existing_tenant.slug == settings.default_tenant_slug
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete the default tenant in single-tenant mode. "
                    "Enable multi-tenant mode or use a different default tenant first.",
                )

            tenant_name = existing_tenant.name
            tenant_slug = existing_tenant.slug

            # Perform the deletion (CASCADE will handle related records)
            stmt = delete(Tenants).where(Tenants.id == tenant_id)
            result = await db.execute(stmt)
            await db.commit()

            if result.rowcount == 0:
                # This shouldn't happen since we checked existence above
                raise HTTPException(status_code=404, detail=f"Tenant with ID {tenant_id} not found")

            logger.warning(
                "Tenant deleted successfully - all related data has been removed",
                tenant_id=str(tenant_id),
                name=tenant_name,
                slug=tenant_slug,
                deleted_records=result.rowcount,
            )

            return {
                "message": f"Tenant '{tenant_name}' ({tenant_slug}) deleted successfully",
                "tenant_id": str(tenant_id),
                "warning": "All related data (users, boards, generations, etc.) has been permanently deleted",  # noqa: E501
            }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("Failed to delete tenant", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete tenant: {str(e)}") from e


@router.get("/status")
async def setup_status() -> dict[str, Any]:
    """
    Get the current setup status of the application.

    This endpoint provides information about:
    - Whether a default tenant exists
    - Current configuration mode
    - Setup recommendations
    """
    try:
        async with get_async_session() as db:
            # Check if default tenant exists
            try:
                default_tenant_id = await ensure_tenant(db, slug=settings.default_tenant_slug)
                has_default_tenant = True
                default_tenant_uuid = str(default_tenant_id)
            except Exception:
                has_default_tenant = False
                default_tenant_uuid = None

        setup_needed = not has_default_tenant and not settings.multi_tenant_mode

        return {
            "setup_needed": setup_needed,
            "has_default_tenant": has_default_tenant,
            "default_tenant_id": default_tenant_uuid,
            "default_tenant_slug": settings.default_tenant_slug,
            "multi_tenant_mode": settings.multi_tenant_mode,
            "auth_provider": settings.auth_provider,
            "recommendations": _get_setup_recommendations(
                setup_needed, has_default_tenant, settings.multi_tenant_mode
            ),
        }

    except Exception as e:
        logger.error("Failed to get setup status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get setup status: {str(e)}") from e


def _get_setup_recommendations(
    setup_needed: bool, has_default_tenant: bool, multi_tenant_mode: bool
) -> list[str]:
    """Get setup recommendations based on current state."""
    recommendations = []

    if setup_needed:
        recommendations.append(
            f"Create a default tenant using POST /api/setup/tenant with slug '{settings.default_tenant_slug}'"  # noqa: E501
        )

    if not has_default_tenant and not multi_tenant_mode:
        recommendations.append(
            "Run database migrations to create the default tenant: 'alembic upgrade head'"
        )

    if settings.auth_provider == "none" and not multi_tenant_mode:
        recommendations.append(
            "Consider configuring a proper authentication provider for production use"
        )

    if not recommendations:
        if multi_tenant_mode:
            recommendations.append("System is ready for multi-tenant operation")
        else:
            recommendations.append("Single-tenant setup is complete and ready to use")

    return recommendations
