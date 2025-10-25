"""
Configuration validation for Boards application.

This module provides validation functions to ensure the application
is properly configured before startup.
"""

from __future__ import annotations

from typing import Any

from .config import settings
from .database.connection import get_async_session, test_database_connection
from .database.seed_data import ensure_default_tenant
from .logging import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when application validation fails."""

    pass


async def validate_database_connection() -> dict[str, Any]:
    """
    Validate that the database is accessible and responsive.

    This runs before other validation checks to catch connection issues early
    with clear error messages.

    Returns a dictionary with validation results and connection details.
    """
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "connection_info": None,
    }

    success, error_message = await test_database_connection()

    if success:
        results["connection_info"] = {
            "status": "connected",
            "message": "Database connection successful",
        }
        logger.info("Database connection validation successful")
    else:
        results["valid"] = False
        results["errors"].append(error_message)
        logger.error("Database connection validation failed", error=error_message)

    return results


async def validate_tenant_configuration() -> dict[str, Any]:
    """
    Validate tenant configuration and setup.

    Returns a dictionary with validation results and recommendations.
    Raises ValidationError if critical validation fails.
    """
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "tenant_info": None,
    }

    try:
        async with get_async_session() as db:
            if settings.multi_tenant_mode:
                # Multi-tenant mode - just validate database connection
                results["tenant_info"] = {
                    "mode": "multi_tenant",
                    "message": "Multi-tenant mode enabled - tenants managed dynamically",
                }
                logger.info("Tenant validation: Multi-tenant mode configured")

            else:
                # Single-tenant mode - ensure default tenant exists
                try:
                    tenant_id = await ensure_default_tenant(db)
                    results["tenant_info"] = {
                        "mode": "single_tenant",
                        "tenant_id": str(tenant_id),
                        "slug": settings.default_tenant_slug,
                        "message": f"Default tenant exists: {tenant_id}",
                    }
                    logger.info(
                        "Tenant validation: Default tenant verified",
                        tenant_id=str(tenant_id),
                        slug=settings.default_tenant_slug,
                    )

                except Exception as e:
                    error_msg = f"Failed to ensure default tenant exists: {str(e)}"
                    results["errors"].append(error_msg)
                    results["valid"] = False
                    logger.error("Tenant validation failed", error=str(e))

    except Exception as e:
        error_msg = f"Database connection failed during tenant validation: {str(e)}"
        results["errors"].append(error_msg)
        results["valid"] = False
        logger.error("Database validation failed", error=str(e))

    return results


async def validate_auth_configuration() -> dict[str, Any]:
    """
    Validate authentication configuration.

    Returns validation results and security recommendations.
    """
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "auth_info": {
            "provider": settings.auth_provider,
            "multi_tenant_mode": settings.multi_tenant_mode,
        },
    }

    # Validate auth provider configuration
    if settings.auth_provider == "none":
        if settings.environment.lower() in ("production", "prod"):
            warning = "No-auth mode detected in production environment - this is a security risk!"
            results["warnings"].append(warning)
            logger.warning(warning)
        else:
            logger.info("Auth validation: No-auth mode enabled for development")

    elif settings.auth_provider == "jwt":
        if not settings.jwt_secret:
            error = "JWT authentication enabled but JWT_SECRET not configured"
            results["errors"].append(error)
            results["valid"] = False
            logger.error(error)
        else:
            logger.info("Auth validation: JWT authentication configured")

    else:
        logger.info(f"Auth validation: Using {settings.auth_provider} provider")

    return results


async def validate_startup_configuration() -> dict[str, Any]:
    """
    Comprehensive startup validation.

    This function should be called during application startup to ensure
    all critical configuration is valid.
    """
    logger.info("Starting application configuration validation")

    # Test database connection first - this catches common issues early
    db_results = await validate_database_connection()

    # Only proceed with other validations if database is accessible
    if db_results["valid"]:
        tenant_results = await validate_tenant_configuration()
        auth_results = await validate_auth_configuration()
    else:
        # Skip tenant/auth validation if database is not accessible
        logger.warning("Skipping tenant and auth validation due to database connection failure")
        tenant_results = {
            "valid": False,
            "warnings": [],
            "errors": ["Skipped due to database connection failure"],
            "tenant_info": None,
        }
        auth_results = await validate_auth_configuration()  # Auth can validate without DB

    # Combine results
    combined_results = {
        "overall_valid": db_results["valid"] and tenant_results["valid"] and auth_results["valid"],
        "database": db_results,
        "tenant": tenant_results,
        "auth": auth_results,
        "environment": {
            "auth_provider": settings.auth_provider,
            "multi_tenant_mode": settings.multi_tenant_mode,
            "environment": settings.environment,
            "debug": settings.debug,
        },
    }

    # Log summary
    if combined_results["overall_valid"]:
        logger.info("Application configuration validation completed successfully")
    else:
        all_errors = (
            db_results.get("errors", [])
            + tenant_results.get("errors", [])
            + auth_results.get("errors", [])
        )
        logger.error(
            "Application configuration validation failed",
            errors=all_errors,
        )

    # Log warnings
    all_warnings = (
        db_results.get("warnings", [])
        + tenant_results.get("warnings", [])
        + auth_results.get("warnings", [])
    )
    if all_warnings:
        logger.warning(
            "Configuration warnings detected",
            warnings=all_warnings,
        )

    return combined_results


def get_startup_recommendations(validation_results: dict[str, Any]) -> list[str]:
    """
    Generate startup recommendations based on validation results.
    """
    recommendations = []

    # Database recommendations
    if not validation_results.get("database", {}).get("valid", False):
        recommendations.append(
            "Database connection failed - check that PostgreSQL is running and accessible"
        )
        return recommendations  # Return early if database is not accessible

    # Tenant recommendations
    tenant_info = validation_results["tenant"].get("tenant_info")
    if tenant_info and tenant_info["mode"] == "single_tenant":
        recommendations.append(f"Single-tenant mode active with tenant: {tenant_info['tenant_id']}")

    # Auth recommendations
    auth_info = validation_results["auth"]["auth_info"]
    if auth_info["provider"] == "none" and settings.environment.lower() not in (
        "development",
        "dev",
    ):
        recommendations.append(
            "Consider configuring a proper authentication provider for non-development environments"
        )

    # Error recommendations
    if not validation_results["overall_valid"]:
        recommendations.append("Fix configuration errors before deploying to production")

    # Success recommendations
    if validation_results["overall_valid"] and not recommendations:
        if auth_info["multi_tenant_mode"]:
            recommendations.append("Multi-tenant configuration is ready for operation")
        else:
            recommendations.append("Single-tenant configuration is ready for operation")

    return recommendations
