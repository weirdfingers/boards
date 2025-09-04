"""
Middleware for request context and logging
"""

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
        'password', 'token', 'api_key', 'secret', 'auth', 'authorization',
        'access_token', 'refresh_token', 'key', 'private_key', 'jwt',
        'session', 'session_id', 'cookie', 'credentials'
    }

    sanitized = {}
    for key, value in params.items():
        # Check if any sensitive keyword is in the parameter name (case insensitive)
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        else:
            sanitized[key] = value

    return sanitized


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

            # Log request start
            logger.info(
                "Request started",
                method=request.method,
                path=request.url.path,
                query_params=sanitized_params,
                user_agent=request.headers.get("user-agent"),
                remote_addr=request.client.host if request.client else None,
            )

            # Process request
            response = await call_next(request)

            # Log request completion
            logger.info(
                "Request completed",
                status_code=response.status_code,
                method=request.method,
                path=request.url.path,
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
