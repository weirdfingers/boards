"""
Centralized logging configuration using structlog
"""

import base64
import logging
import os
import secrets
import sys
import time
from contextvars import ContextVar
from typing import Any

import structlog
from fastapi import Request

# Context variables for request tracking
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


def _rename_event_to_message(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Rename 'event' to 'message' for Google Cloud Logging compatibility."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def _level_to_severity(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Convert 'level' to 'severity' with uppercase value for Google Cloud Logging."""
    if "level" in event_dict:
        level = event_dict.pop("level")
        # Map structlog levels to Google Cloud Logging severity levels
        severity_map = {
            "debug": "DEBUG",
            "info": "INFO",
            "warning": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL",
        }
        event_dict["severity"] = severity_map.get(level.lower(), "DEFAULT")
    return event_dict


class RequestContextFilter:
    """Add request context to log records."""

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        """Add request context to the event dict."""
        # Suppress unused parameter warnings - these are required by structlog interface
        _ = logger, method_name

        request_id = request_id_ctx.get()
        user_id = user_id_ctx.get()

        if request_id:
            event_dict["request_id"] = request_id

        if user_id:
            event_dict["user_id"] = user_id

        return event_dict


def configure_logging(debug: bool = False, google_logging_compat: bool = False) -> None:
    """Configure structlog with appropriate processors and formatters."""

    # Determine log level
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure stdlib logging
    logging.basicConfig(
        level=log_level,
        stream=sys.stdout,
        format="%(message)s",
        force=True,
    )

    # Silence noisy third-party loggers that spam at DEBUG level
    # These HTTP libraries output verbose protocol-level details (HPACK encoding, etc.)
    noisy_loggers = [
        "httpx",
        "httpcore",
        "httpcore.http2",
        "httpcore.http11",
        "httpcore.connection",
        "hpack",
        "h2",
        "h11",
        "urllib3",
        "urllib3.connectionpool",
        "asyncio",
        "watchfiles",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Configure structlog processors
    processors = [
        # Add context vars to the event dict from the OpenTelemetry context
        structlog.contextvars.merge_contextvars,
        # Filter out keys with underscores (internal)
        structlog.stdlib.filter_by_level,
        # Add logger name to event dict
        structlog.stdlib.add_logger_name,
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add request context
        RequestContextFilter(),
        # Add timestamp
        structlog.processors.TimeStamper(fmt="ISO", utc=True),
        # Perform %-style string formatting
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Stack info processor (for exceptions)
        structlog.processors.StackInfoRenderer(),
        # Exception info processor
        structlog.processors.format_exc_info,
        # Unicode decoder processor
        structlog.processors.UnicodeDecoder(),
    ]

    # Add OpenTelemetry trace_id and span_id to logs if available
    try:
        from opentelemetry import trace

        def add_opentelemetry_context(logger, method_name, event_dict):
            span = trace.get_current_span()
            # Check if span is valid by checking if it has a context
            if span.get_span_context().is_valid:
                span_context = span.get_span_context()
                event_dict["trace_id"] = f"{span_context.trace_id:032x}"
                event_dict["span_id"] = f"{span_context.span_id:016x}"
                # For GCP Cloud Logging correlation
                project_id = os.environ.get("GCP_PROJECT_ID", "")
                event_dict["logging.googleapis.com/trace"] = (
                    f"projects/{project_id}/traces/{event_dict['trace_id']}"
                )
                event_dict["logging.googleapis.com/spanId"] = event_dict["span_id"]
            return event_dict

        processors.insert(1, add_opentelemetry_context)
    except ImportError:
        pass

    if debug:
        # Development: human-readable console output
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    elif google_logging_compat:
        # Production with GCP: JSON with Cloud Logging field names
        processors.extend(
            [
                _level_to_severity,
                _rename_event_to_message,
                structlog.processors.JSONRenderer(),
            ]
        )
    else:
        # Production: standard JSON output
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def generate_request_id() -> str:
    """Generate a compact, secure request ID with timestamp and randomness.

    Uses microsecond precision timestamp with added randomness for security.
    Format: 11-character base64 string (e.g., 'Ab3X9mF2xYz')

    Provides high uniqueness probability while preventing predictable enumeration.
    """
    # Get microseconds since epoch (8 bytes when encoded as int64)
    timestamp_us = int(time.time() * 1_000_000)

    # Add 2 bytes of cryptographically secure randomness
    random_bytes = secrets.token_bytes(2)

    # Convert timestamp to bytes (8 bytes for int64) and combine with random bytes
    timestamp_bytes = timestamp_us.to_bytes(8, byteorder="big")
    combined_bytes = timestamp_bytes + random_bytes

    # Encode as base64 and strip padding
    b64 = base64.urlsafe_b64encode(combined_bytes).decode("ascii").rstrip("=")

    return b64


def set_request_context(request_id: str | None = None, user_id: str | None = None) -> None:
    """Set request context variables.

    Args:
        request_id: Request ID to set (generates one if None)
        user_id: User ID to set
    """
    if request_id is None:
        request_id = generate_request_id()

    request_id_ctx.set(request_id)
    if user_id is not None:
        user_id_ctx.set(user_id)


def clear_request_context() -> None:
    """Clear request context variables."""
    request_id_ctx.set(None)
    user_id_ctx.set(None)


def get_request_id() -> str | None:
    """Get the current request ID."""
    return request_id_ctx.get()


def get_user_id() -> str | None:
    """Get the current user ID."""
    return user_id_ctx.get()


def extract_user_id_from_request(request: Request) -> str | None:
    """Extract user ID from FastAPI request.

    This should be customized based on your authentication implementation.

    Args:
        request: FastAPI request object

    Returns:
        User ID if authenticated, None otherwise
    """
    # TODO: Implement based on your auth strategy
    # Examples:
    # - JWT token in Authorization header
    # - Session data
    # - Supabase auth token

    # For now, look for a user ID in headers (customize as needed)
    auth_header = request.headers.get("authorization")
    if auth_header:
        # This is a placeholder - implement actual token parsing
        # For example, if using Bearer tokens:
        # if auth_header.startswith("Bearer "):
        #     token = auth_header[7:]
        #     # Parse JWT token to extract user_id
        #     return parsed_user_id

        # For now, return None until auth is implemented
        return None

    return None
