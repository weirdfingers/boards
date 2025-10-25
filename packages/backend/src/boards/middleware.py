"""
Middleware for request context and logging
"""

import json
import re
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .logging import (
    clear_request_context,
    extract_user_id_from_request,
    get_logger,
    set_request_context,
)

logger = get_logger(__name__)


def sanitize_query_params(params: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive query parameters from logging.

    Args:
        params: Dictionary of query parameters

    Returns:
        Dictionary with sensitive parameters redacted
    """
    sensitive_keys = {
        "password",
        "token",
        "api_key",
        "secret",
        "auth",
        "authorization",
        "access_token",
        "refresh_token",
        "key",
        "private_key",
        "jwt",
        "session",
        "session_id",
        "cookie",
        "credentials",
    }

    sanitized = {}
    for key, value in params.items():
        # Check if any sensitive keyword is in the parameter name (case insensitive)
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value

    return sanitized


# 1) Extend extractor to support GET /graphql as well
async def extract_graphql_operation_name(request: Request) -> str | None:
    if request.url.path != "/graphql":
        return None

    # Handle GET /graphql (operationName in query params, or parse from query)
    if request.method == "GET":
        params = dict(request.query_params)
        op = params.get("operationName")
        if isinstance(op, str) and op:
            return op

        q = params.get("query", "")
        if not isinstance(q, str) or not q:
            return None
        if "__schema" in q or "IntrospectionQuery" in q:
            return "__introspection"

        match = re.search(r"\bquery\s+(\w+)", q) or re.search(r"\bmutation\s+(\w+)", q)
        if match:
            kind = "mutation:" if q.lstrip().startswith("mutation") else ""
            return f"{kind}{match.group(1)}"
        return "unnamed_operation"

    # Existing POST /graphql logic
    if request.method == "POST":
        try:
            body = await request.body()
            if not body:
                return None
            data = json.loads(body)
            op = data.get("operationName")
            if isinstance(op, str) and op:
                return op
            q = data.get("query", "")
            if not isinstance(q, str) or not q:
                return None
            if "__schema" in q or "IntrospectionQuery" in q:
                return "__introspection"
            m = re.search(r"\bquery\s+(\w+)", q) or re.search(r"\bmutation\s+(\w+)", q)
            if m:
                kind = "mutation:" if q.lstrip().startswith("mutation") else ""
                return f"{kind}{m.group(1)}"
            return "unnamed_operation"
        except (json.JSONDecodeError, TypeError):
            return None

    return None


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set logging context for each request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and set logging context."""

        # Extract user ID from request (implement based on your auth)
        user_id = extract_user_id_from_request(request)

        # Set request context
        set_request_context(user_id=user_id)

        try:
            # Sanitize query parameters for logging
            sanitized_params = None
            if request.query_params:
                sanitized_params = sanitize_query_params(dict(request.query_params))
                # If hitting /graphql, never log raw GraphQL payload in query string
                # Comment this out to see the raw GraphQL payload in the query string
                if request.url.path == "/graphql" and isinstance(sanitized_params, dict):
                    for k in ("query", "variables", "extensions"):
                        if k in sanitized_params:
                            sanitized_params[k] = "[REDACTED]"

            # Extract GraphQL operation name if applicable
            graphql_operation = await extract_graphql_operation_name(request)

            # Log request start
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "query_params": sanitized_params,
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": request.client.host if request.client else None,
            }

            # Add GraphQL operation name if available
            if graphql_operation:
                log_data["graphql_operation"] = graphql_operation

            logger.info("Request started", **log_data)

            # Process request
            response = await call_next(request)

            # Log request completion
            logger.info(
                "Request completed",
                status_code=response.status_code,
                method=request.method,
                path=request.url.path,
                graphql_operation=graphql_operation,  # Include in completion log too
            )

            return response

        except Exception as e:
            # Log request error
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
            )
            raise

        finally:
            # Clear context
            clear_request_context()


class TenantRoutingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tenant-aware request routing and validation.

    This middleware:
    1. Validates X-Tenant headers in multi-tenant mode
    2. Enforces tenant isolation rules
    3. Sets up request context for tenant-scoped operations
    4. Provides early tenant validation before auth processing
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant routing and validation."""

        # Extract tenant information from headers
        x_tenant = request.headers.get("X-Tenant")

        # Log incoming request with tenant info
        logger.debug(
            "Processing request with tenant context",
            method=request.method,
            path=request.url.path,
            x_tenant=x_tenant,
            multi_tenant_mode=settings.multi_tenant_mode,
        )

        # Validate tenant header in multi-tenant mode
        if settings.multi_tenant_mode:
            tenant_validation_result = await self._validate_tenant_header(x_tenant, request)
            if tenant_validation_result is not None:
                return tenant_validation_result

        # Add tenant context to request state for downstream use
        request.state.tenant_slug = x_tenant or settings.default_tenant_slug
        request.state.multi_tenant_mode = settings.multi_tenant_mode

        try:
            response = await call_next(request)

            # Add tenant information to response headers for debugging
            if settings.debug:
                response.headers["X-Tenant-Resolved"] = request.state.tenant_slug
                if settings.multi_tenant_mode:
                    response.headers["X-Multi-Tenant-Mode"] = "true"

            return response

        except Exception as e:
            logger.error(
                "Request processing failed",
                error=str(e),
                tenant_slug=getattr(request.state, "tenant_slug", "unknown"),
                path=request.url.path,
            )
            raise

    async def _validate_tenant_header(
        self, x_tenant: str | None, request: Request
    ) -> Response | None:
        """
        Validate X-Tenant header in multi-tenant mode.

        Returns:
            Response if validation fails (error response), None if validation passes
        """
        from fastapi.responses import JSONResponse

        # In multi-tenant mode, some endpoints may require X-Tenant header
        if self._requires_tenant_header(request):
            if not x_tenant:
                logger.warning(
                    "Missing required X-Tenant header in multi-tenant mode",
                    path=request.url.path,
                    method=request.method,
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Missing X-Tenant header",
                        "detail": (
                            "X-Tenant header is required in multi-tenant mode " "for this endpoint"
                        ),
                        "multi_tenant_mode": True,
                    },
                )

        # Validate tenant slug format if provided
        if x_tenant:
            validation_error = self._validate_tenant_slug_format(x_tenant)
            if validation_error:
                logger.warning(
                    "Invalid X-Tenant header format",
                    x_tenant=x_tenant,
                    error=validation_error,
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid X-Tenant header format",
                        "detail": validation_error,
                        "provided_tenant": x_tenant,
                    },
                )

        return None  # Validation passed

    def _requires_tenant_header(self, request: Request) -> bool:
        """
        Determine if the request requires an X-Tenant header.

        In multi-tenant mode, most API endpoints require tenant specification,
        except for certain system endpoints like health checks.
        """
        path = request.url.path

        # System endpoints that don't require tenant specification
        system_endpoints = {
            "/health",
            "/api/setup/status",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

        if path in system_endpoints:
            return False

        # Setup endpoints are special - they help create tenants
        if path.startswith("/api/setup/"):
            return False

        # All other API endpoints require tenant in multi-tenant mode
        if path.startswith("/api/") or path.startswith("/graphql"):
            return True

        return False

    def _validate_tenant_slug_format(self, tenant_slug: str) -> str | None:
        """
        Validate tenant slug format.

        Returns:
            Error message if invalid, None if valid
        """
        if not tenant_slug:
            return "Tenant slug cannot be empty"

        if len(tenant_slug) > 255:
            return "Tenant slug too long (max 255 characters)"

        if not re.match(r"^[a-z0-9-]+$", tenant_slug):
            return "Tenant slug must contain only lowercase letters, numbers, and hyphens"

        if tenant_slug.startswith("-") or tenant_slug.endswith("-"):
            return "Tenant slug cannot start or end with hyphen"

        return None  # Valid
