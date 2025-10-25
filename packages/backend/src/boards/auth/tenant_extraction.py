"""
Tenant extraction utilities for multi-tenant authentication.

This module provides utilities to extract tenant information from JWT/OIDC claims
and other authentication contexts.
"""

from __future__ import annotations

from typing import Any

from ..config import settings
from ..logging import get_logger
from .context import Principal

logger = get_logger(__name__)


def extract_tenant_from_claims(
    principal: Principal,
    fallback_tenant: str | None = None,
) -> str:
    """
    Extract tenant slug from JWT/OIDC claims.

    This function supports multiple tenant extraction strategies:
    1. Direct 'tenant' claim in JWT
    2. Organization-based claims (org, organization, org_slug)
    3. Custom claims (configurable via settings)
    4. Domain-based extraction from email
    5. Fallback to header or default

    Args:
        principal: Principal with claims from JWT/OIDC
        fallback_tenant: Fallback tenant slug if no tenant found in claims

    Returns:
        Tenant slug extracted from claims or fallback
    """
    claims = principal.get("claims", {})

    if not claims:
        logger.debug("No claims available in principal, using fallback")
        return fallback_tenant or settings.default_tenant_slug

    # Strategy 1: Direct tenant claim
    if tenant_slug := claims.get("tenant"):
        logger.info("Extracted tenant from 'tenant' claim", tenant_slug=tenant_slug)
        return _validate_tenant_slug(tenant_slug)

    # Strategy 2: Organization-based claims
    org_claims = ["org", "organization", "org_slug", "org_name"]
    for claim_name in org_claims:
        if org_value := claims.get(claim_name):
            tenant_slug = _normalize_tenant_slug(org_value)
            logger.info(
                "Extracted tenant from organization claim",
                claim_name=claim_name,
                org_value=org_value,
                tenant_slug=tenant_slug,
            )
            return tenant_slug

    # Strategy 3: Custom claims (configurable)
    custom_tenant_claim = getattr(settings, "jwt_tenant_claim", None)
    if custom_tenant_claim and (custom_value := claims.get(custom_tenant_claim)):
        tenant_slug = _normalize_tenant_slug(custom_value)
        logger.info(
            "Extracted tenant from custom claim",
            claim_name=custom_tenant_claim,
            custom_value=custom_value,
            tenant_slug=tenant_slug,
        )
        return tenant_slug

    # Strategy 4: Domain-based extraction from email
    if settings.multi_tenant_mode and (email := claims.get("email")):
        tenant_slug = _extract_tenant_from_email_domain(email)
        if tenant_slug:
            logger.info(
                "Extracted tenant from email domain",
                email=email,
                tenant_slug=tenant_slug,
            )
            return tenant_slug

    # Strategy 5: Namespace/sub-organization claims
    namespace_claims = ["namespace", "group", "team", "workspace"]
    for claim_name in namespace_claims:
        if namespace_value := claims.get(claim_name):
            tenant_slug = _normalize_tenant_slug(namespace_value)
            logger.info(
                "Extracted tenant from namespace claim",
                claim_name=claim_name,
                namespace_value=namespace_value,
                tenant_slug=tenant_slug,
            )
            return tenant_slug

    # No tenant found in claims, use fallback
    logger.debug(
        "No tenant information found in JWT/OIDC claims",
        available_claims=list(claims.keys()),
        using_fallback=fallback_tenant or settings.default_tenant_slug,
    )
    return fallback_tenant or settings.default_tenant_slug


def extract_tenant_from_oidc_userinfo(
    userinfo: dict[str, Any],
    fallback_tenant: str | None = None,
) -> str:
    """
    Extract tenant slug from OIDC userinfo endpoint response.

    Args:
        userinfo: Response from OIDC userinfo endpoint
        fallback_tenant: Fallback tenant slug if no tenant found

    Returns:
        Tenant slug extracted from userinfo or fallback
    """
    if not userinfo:
        return fallback_tenant or settings.default_tenant_slug

    # Similar extraction strategies as claims
    if tenant_slug := userinfo.get("tenant"):
        return _validate_tenant_slug(tenant_slug)

    # Organization-based extraction
    for org_field in ["organization", "org", "company"]:
        if org_value := userinfo.get(org_field):
            return _normalize_tenant_slug(org_value)

    # Groups/roles extraction
    if groups := userinfo.get("groups", []):
        if isinstance(groups, list) and groups:
            # Use first group as tenant
            return _normalize_tenant_slug(groups[0])

    return fallback_tenant or settings.default_tenant_slug


def _normalize_tenant_slug(value: Any) -> str:
    """
    Normalize a value to a valid tenant slug.

    Args:
        value: Value to normalize (string, dict, etc.)

    Returns:
        Normalized tenant slug
    """
    if isinstance(value, dict):
        # Extract slug if it's an object with slug/id fields
        return _normalize_tenant_slug(value.get("slug") or value.get("id") or value.get("name", ""))

    # Convert to string and normalize
    slug = str(value).lower().strip()

    # Replace spaces and invalid characters with hyphens
    import re

    slug = re.sub(r"[^a-z0-9-]", "-", slug)

    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Ensure it's not empty and not too long
    if not slug:
        slug = "unknown"
    elif len(slug) > 50:  # Reasonable limit for tenant slugs
        slug = slug[:50].rstrip("-")

    return slug


def _validate_tenant_slug(slug: str) -> str:
    """
    Validate a tenant slug format.

    Args:
        slug: Tenant slug to validate

    Returns:
        Validated slug

    Raises:
        ValueError: If slug is invalid
    """
    if not slug:
        raise ValueError("Tenant slug cannot be empty")

    if len(slug) > 255:
        raise ValueError("Tenant slug too long (max 255 characters)")

    import re

    if not re.match(r"^[a-z0-9-]+$", slug):
        raise ValueError("Tenant slug must contain only lowercase letters, numbers, and hyphens")

    if slug.startswith("-") or slug.endswith("-"):
        raise ValueError("Tenant slug cannot start or end with hyphen")

    return slug


def _extract_tenant_from_email_domain(email: str) -> str | None:
    """
    Extract tenant slug from email domain.

    This is useful for organizations that want to automatically
    assign tenants based on email domains.

    Args:
        email: Email address

    Returns:
        Tenant slug derived from domain, or None if not applicable
    """
    try:
        domain = email.split("@")[1].lower()

        # Skip common public email domains
        public_domains = {
            "gmail.com",
            "yahoo.com",
            "outlook.com",
            "hotmail.com",
            "icloud.com",
            "protonmail.com",
            "aol.com",
        }

        if domain in public_domains:
            logger.debug(
                "Skipping tenant extraction from public email domain",
                domain=domain,
            )
            return None

        # Extract organization name from domain
        # e.g., "user@acme-corp.com" -> "acme-corp"
        org_name = domain.split(".")[0]
        return _normalize_tenant_slug(org_name)

    except (IndexError, AttributeError):
        logger.warning("Invalid email format for domain extraction", email=email)
        return None


def get_tenant_extraction_config() -> dict[str, Any]:
    """
    Get current tenant extraction configuration.

    Returns:
        Dictionary with tenant extraction settings
    """
    return {
        "multi_tenant_mode": settings.multi_tenant_mode,
        "default_tenant_slug": settings.default_tenant_slug,
        "custom_tenant_claim": getattr(settings, "jwt_tenant_claim", None),
        "domain_based_extraction": settings.multi_tenant_mode,
        "supported_claim_names": [
            "tenant",
            "org",
            "organization",
            "org_slug",
            "org_name",
            "namespace",
            "group",
            "team",
            "workspace",
        ],
    }
