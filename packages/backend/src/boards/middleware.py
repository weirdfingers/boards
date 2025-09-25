"""
Middleware for request context and logging
"""

import json
import re  # Added for operation name extraction
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

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


async def extract_graphql_operation_name(request: Request) -> str | None:
    """Extract GraphQL operation name from request body.

    Only attempts to parse for POST requests to /graphql.
    Returns None if not a GraphQL request or parsing fails.
    """
    if not (request.method == "POST" and request.url.path == "/graphql"):
        return None

    try:
        # Get the request body (this consumes it)
        body = await request.body()
        if not body:
            return None

        # Parse the JSON request wrapper
        request_data = json.loads(body)

        # 1. First try to get explicit operationName
        operation_name = request_data.get("operationName")
        if operation_name and isinstance(operation_name, str):
            return operation_name

        # 2. Check if we have a query field
        query = request_data.get("query", "")
        if not query:
            return None

        # 3. For introspection queries, return special identifier
        if "__schema" in query or "IntrospectionQuery" in query:
            return "__introspection"

        # 4. For other queries, extract first operation name
        match = re.search(r"query\s+(\w+)", query)
        if match:
            return match.group(1)

        # 5. For mutations
        match = re.search(r"mutation\s+(\w+)", query)
        if match:
            return f"mutation:{match.group(1)}"

        return "unnamed_operation"

    except (json.JSONDecodeError, TypeError):
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
