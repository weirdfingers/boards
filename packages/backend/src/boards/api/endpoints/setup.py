"""
Setup endpoints for initial tenant configuration.

These endpoints help with one-time setup for single-tenant deployments
or initial configuration of multi-tenant environments.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...config import settings
from ...database.connection import get_async_session
from ...database.seed_data import ensure_tenant, seed_tenant_with_data
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
        pattern=r'^[a-z0-9-]+$',
        description="URL-safe slug for the tenant (lowercase, numbers, hyphens only)"
    )
    settings: dict[str, Any] = Field(
        default_factory=dict, description="Optional tenant-specific settings"
    )
    include_sample_data: bool = Field(
        default=False, description="Whether to include sample boards and data"
    )


class TenantSetupResponse(BaseModel):
    """Response model for tenant setup."""

    tenant_id: str = Field(..., description="UUID of the created tenant")
    name: str = Field(..., description="Display name of the tenant")
    slug: str = Field(..., description="Slug of the tenant")
    message: str = Field(..., description="Success message")
    existing: bool = Field(..., description="Whether tenant already existed")


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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup tenant: {str(e)}"
        ) from e


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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get setup status: {str(e)}"
        ) from e


def _get_setup_recommendations(
    setup_needed: bool, has_default_tenant: bool, multi_tenant_mode: bool
) -> list[str]:
    """Get setup recommendations based on current state."""
    recommendations = []

    if setup_needed:
        recommendations.append(
            f"Create a default tenant using POST /api/setup/tenant with slug '{settings.default_tenant_slug}'"
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