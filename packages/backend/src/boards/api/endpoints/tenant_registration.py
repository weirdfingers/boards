"""
Self-service tenant registration endpoints.

This module provides endpoints for organizations to register new tenants
in multi-tenant mode, with optional approval workflows.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ...auth.context import AuthContext
from ...auth.middleware import get_auth_context
from ...config import settings
from ...database.connection import get_async_session
from ...database.seed_data import ensure_tenant, seed_tenant_with_data
from ...logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class TenantRegistrationRequest(BaseModel):
    """Request model for self-service tenant registration."""

    organization_name: str = Field(
        ..., min_length=1, max_length=255, description="Organization name for the new tenant"
    )
    organization_slug: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
        description="Desired tenant slug (auto-generated if not provided)",
    )
    admin_email: str = Field(..., description="Email of the organization administrator")
    admin_name: str | None = Field(None, description="Full name of the organization administrator")
    use_case: str | None = Field(
        None, max_length=500, description="Brief description of intended use case"
    )
    organization_size: str | None = Field(
        None, description="Size of organization (small, medium, large, enterprise)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional registration metadata"
    )
    include_sample_data: bool = Field(
        default=True, description="Whether to include sample boards and data"
    )

    @field_validator("admin_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        import re

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("organization_size")
    @classmethod
    def validate_organization_size(cls, v: str | None) -> str | None:
        """Validate organization size values."""
        if v is not None:
            valid_sizes = {"small", "medium", "large", "enterprise"}
            if v.lower() not in valid_sizes:
                raise ValueError(f'Organization size must be one of: {", ".join(valid_sizes)}')
        return v.lower() if v else None


class TenantRegistrationResponse(BaseModel):
    """Response model for tenant registration."""

    tenant_id: str = Field(..., description="UUID of the registered tenant")
    organization_name: str = Field(..., description="Organization name")
    tenant_slug: str = Field(..., description="Assigned tenant slug")
    status: str = Field(..., description="Registration status")
    admin_instructions: str = Field(..., description="Next steps for the administrator")
    dashboard_url: str | None = Field(None, description="URL to access tenant dashboard")
    api_access: dict[str, Any] = Field(..., description="API access information")


class TenantRegistrationStatus(BaseModel):
    """Model for checking registration status."""

    enabled: bool = Field(..., description="Whether self-service registration is enabled")
    requires_approval: bool = Field(..., description="Whether registrations require approval")
    max_tenants_per_user: int | None = Field(None, description="Maximum tenants per user")
    allowed_domains: list[str] | None = Field(None, description="Allowed email domains")


@router.get("/registration/status", response_model=TenantRegistrationStatus)
async def get_registration_status() -> TenantRegistrationStatus:
    """
    Get the current tenant registration status and configuration.
    """
    return TenantRegistrationStatus(
        enabled=settings.multi_tenant_mode,
        requires_approval=getattr(settings, "tenant_registration_requires_approval", False),
        max_tenants_per_user=getattr(settings, "max_tenants_per_user", None),
        allowed_domains=getattr(settings, "tenant_registration_allowed_domains", None),
    )


@router.post("/register", response_model=TenantRegistrationResponse)
async def register_tenant(
    request: TenantRegistrationRequest,
    auth_context: AuthContext = Depends(get_auth_context),
) -> TenantRegistrationResponse:
    """
    Register a new tenant for an organization.

    This endpoint allows authenticated users to create new tenants for their
    organizations. In multi-tenant mode, this enables self-service onboarding.

    Requirements:
    - Multi-tenant mode must be enabled
    - User must be authenticated
    - Organization slug must be unique
    - Optional: email domain validation
    - Optional: approval workflow
    """

    # Validate prerequisites
    if not settings.multi_tenant_mode:
        raise HTTPException(
            status_code=400, detail="Tenant registration is only available in multi-tenant mode"
        )

    if not auth_context.user_id:
        raise HTTPException(
            status_code=401, detail="Authentication required for tenant registration"
        )

    # Validate email domain if restrictions are configured
    allowed_domains = getattr(settings, "tenant_registration_allowed_domains", None)
    if allowed_domains:
        admin_domain = request.admin_email.split("@")[1].lower()
        if admin_domain not in allowed_domains:
            raise HTTPException(
                status_code=400,
                detail=f"Email domain '{admin_domain}' is not allowed for registration",
            )

    # Check if user has reached tenant limit
    max_tenants = getattr(settings, "max_tenants_per_user", None)
    if max_tenants:
        # TODO: Implement tenant count check per user
        logger.warning(
            "Tenant limit check not implemented",
            user_id=str(auth_context.user_id),
            max_tenants=max_tenants,
        )

    # Generate tenant slug if not provided
    tenant_slug = request.organization_slug
    if not tenant_slug:
        tenant_slug = _generate_slug_from_name(request.organization_name)

    logger.info(
        "Processing tenant registration request",
        organization_name=request.organization_name,
        tenant_slug=tenant_slug,
        admin_email=request.admin_email,
        user_id=str(auth_context.user_id),
    )

    try:
        async with get_async_session() as db:
            # Create tenant with sample data
            if request.include_sample_data:
                tenant_id = await seed_tenant_with_data(
                    db,
                    tenant_name=request.organization_name,
                    tenant_slug=tenant_slug,
                    tenant_settings={
                        "admin_email": request.admin_email,
                        "admin_name": request.admin_name,
                        "use_case": request.use_case,
                        "organization_size": request.organization_size,
                        "registered_by": str(auth_context.user_id),
                        "registration_metadata": request.metadata,
                    },
                    include_sample_data=True,
                )
            else:
                tenant_id = await ensure_tenant(
                    db,
                    name=request.organization_name,
                    slug=tenant_slug,
                    settings_dict={
                        "admin_email": request.admin_email,
                        "admin_name": request.admin_name,
                        "use_case": request.use_case,
                        "organization_size": request.organization_size,
                        "registered_by": str(auth_context.user_id),
                        "registration_metadata": request.metadata,
                    },
                )

            # Determine status based on approval requirements
            requires_approval = getattr(settings, "tenant_registration_requires_approval", False)
            status = "pending_approval" if requires_approval else "active"

            # Generate dashboard URL if available
            dashboard_url = _generate_dashboard_url(tenant_slug)

            logger.info(
                "Tenant registration completed",
                tenant_id=str(tenant_id),
                tenant_slug=tenant_slug,
                status=status,
                admin_email=request.admin_email,
            )

            return TenantRegistrationResponse(
                tenant_id=str(tenant_id),
                organization_name=request.organization_name,
                tenant_slug=tenant_slug,
                status=status,
                admin_instructions=_generate_admin_instructions(status, tenant_slug),
                dashboard_url=dashboard_url,
                api_access={
                    "tenant_header": f"X-Tenant: {tenant_slug}",
                    "graphql_endpoint": "/graphql",
                    "api_base_url": "/api",
                    "authentication_required": True,
                },
            )

    except Exception as e:
        logger.error(
            "Tenant registration failed",
            error=str(e),
            organization_name=request.organization_name,
            tenant_slug=tenant_slug,
        )
        raise HTTPException(status_code=500, detail=f"Failed to register tenant: {str(e)}") from e


def _generate_slug_from_name(organization_name: str) -> str:
    """Generate a URL-safe slug from organization name."""
    import re
    import uuid

    # Basic normalization
    slug = organization_name.lower().strip()

    # Replace spaces and special characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Ensure it's not empty
    if not slug or len(slug) < 3:
        slug = f"org-{uuid.uuid4().hex[:8]}"

    # Ensure it's not too long
    if len(slug) > 50:
        slug = slug[:47] + f"-{uuid.uuid4().hex[:2]}"

    return slug


def _generate_dashboard_url(tenant_slug: str) -> str | None:
    """Generate dashboard URL for the tenant."""
    # This would typically point to your frontend application
    frontend_base_url = getattr(settings, "frontend_base_url", None)
    if frontend_base_url:
        return f"{frontend_base_url}/?tenant={tenant_slug}"
    return None


def _generate_admin_instructions(status: str, tenant_slug: str) -> str:
    """Generate setup instructions for the tenant administrator."""
    if status == "pending_approval":
        return (
            "Your tenant registration is pending approval. "
            "You will receive an email notification when your tenant is activated. "
            f"Your tenant slug is '{tenant_slug}' - save this for future reference."
        )
    else:
        return (
            f"Your tenant '{tenant_slug}' is ready to use! "
            "Include the X-Tenant header in all API requests. "
            "Visit the dashboard to get started with boards and content generation."
        )
