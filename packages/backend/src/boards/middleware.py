"""
Middleware for request context and logging
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import set_request_context, clear_request_context, extract_user_id_from_request, get_logger

logger = get_logger(__name__)


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set logging context for each request."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and set logging context."""
        
        # Extract user ID from request (implement based on your auth)
        user_id = extract_user_id_from_request(request)
        
        # Set request context
        set_request_context(user_id=user_id)
        
        try:
            # Log request start
            logger.info(
                "Request started",
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params) if request.query_params else None,
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
                exc_info=True,
            )
            raise
            
        finally:
            # Clear context
            clear_request_context()