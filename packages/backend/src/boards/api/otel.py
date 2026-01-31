"""
OpenTelemetry instrumentation setup for Boards API.

This module handles:
- TracerProvider configuration for Cloud Trace (production) and OTLP/Jaeger (local)
- FastAPI instrumentation
- AsyncPG database tracing (including PreparedStatement patching for SQLAlchemy async)
- HTTPX client instrumentation
- Span filtering to reduce noise from transaction management
"""

import os

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class FilteringSpanProcessor(BatchSpanProcessor):
    """
    SpanProcessor that filters out noisy database transaction spans.
    Keeps actual SQL queries while removing connect/BEGIN/COMMIT/ROLLBACK noise.
    """

    FILTERED_SPAN_NAMES = frozenset({"connect"})

    def on_end(self, span: ReadableSpan) -> None:
        if span.name in self.FILTERED_SPAN_NAMES:
            return
        super().on_end(span)


def _instrument_prepared_statements(tracer_provider: TracerProvider) -> None:
    """
    Instrument asyncpg PreparedStatement methods for tracing.

    SQLAlchemy async uses prepared statements which bypass the standard
    Connection.execute/fetch methods that AsyncPGInstrumentor patches.
    This function adds tracing for PreparedStatement.fetch/fetchval/fetchrow.
    """
    import wrapt
    from opentelemetry.semconv._incubating.attributes.db_attributes import (
        DB_NAME,
        DB_STATEMENT,
        DB_SYSTEM,
    )
    from opentelemetry.trace import SpanKind

    tracer = trace.get_tracer(__name__, tracer_provider=tracer_provider)

    def _get_span_name(query: str) -> str:
        """Extract operation name from SQL query."""
        if not query:
            return "DB"
        # Get first word (SELECT, INSERT, UPDATE, DELETE, etc.)
        parts = query.strip().split(None, 1)
        return parts[0].upper() if parts else "DB"

    async def _traced_prepared_stmt(wrapped, instance, args, kwargs):
        """Wrapper for PreparedStatement methods that adds tracing."""
        query = getattr(instance, "_query", None) or ""
        span_name = _get_span_name(query)

        with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
            if span.is_recording():
                span.set_attribute(DB_SYSTEM, "postgresql")
                span.set_attribute(DB_STATEMENT, query)
                # Try to get database name from connection
                conn = getattr(instance, "_connection", None)
                if conn:
                    params = getattr(conn, "_params", None)
                    if params:
                        dbname = getattr(params, "database", None)
                        if dbname:
                            span.set_attribute(DB_NAME, dbname)

            return await wrapped(*args, **kwargs)

    # Patch PreparedStatement methods using wrapt
    for method_name in ["fetch", "fetchval", "fetchrow"]:
        wrapt.wrap_function_wrapper(
            "asyncpg.prepared_stmt",
            f"PreparedStatement.{method_name}",
            _traced_prepared_stmt,
        )

    logger.debug("PreparedStatement instrumentation applied")


def setup_opentelemetry(app) -> None:
    """
    Configure OpenTelemetry instrumentation for the FastAPI application.

    Enables tracing in:
    - Production: sends to Google Cloud Trace
    - Local development: sends to Jaeger via OTLP when BOARDS_OTEL_ENABLED=true

    Args:
        app: The FastAPI application instance to instrument
    """
    is_production = settings.environment.lower() in ("production", "prod")
    is_local_otel = (
        settings.environment.lower() not in ("production", "prod") and settings.otel_enabled
    )

    if not (is_production or is_local_otel):
        logger.debug("OpenTelemetry instrumentation disabled")
        return

    try:
        # Configure resource with service name from settings
        resource = Resource.create({SERVICE_NAME: settings.otel_service_name})
        tracer_provider = TracerProvider(resource=resource)

        if is_production:
            # Production: send to Google Cloud Trace
            project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
            cloud_trace_exporter = CloudTraceSpanExporter(project_id=project_id)
            tracer_provider.add_span_processor(FilteringSpanProcessor(cloud_trace_exporter))
            logger.info(
                "OpenTelemetry configured for Cloud Trace",
                project_id=project_id,
                service_name=settings.otel_service_name,
            )
        else:
            # Local: send to Jaeger via OTLP
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint, insecure=True)
            tracer_provider.add_span_processor(FilteringSpanProcessor(otlp_exporter))
            logger.info(
                "OpenTelemetry configured for OTLP",
                endpoint=settings.otel_endpoint,
                service_name=settings.otel_service_name,
            )

        trace.set_tracer_provider(tracer_provider)

        # Instrument FastAPI
        # We add excluded_urls to avoid tracing health checks which clutter the traces
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=tracer_provider,
            excluded_urls="health,status,metrics",
        )

        # Instrument AsyncPG for database tracing
        # The standard AsyncPGInstrumentor only wraps Connection methods, but SQLAlchemy
        # async uses PreparedStatements which need separate instrumentation
        try:
            from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

            AsyncPGInstrumentor().instrument(tracer_provider=tracer_provider)

            # Patch PreparedStatement methods to capture actual SQL queries
            # SQLAlchemy async uses prepared statements, bypassing Connection.execute/fetch
            _instrument_prepared_statements(tracer_provider)

            logger.info("AsyncPG instrumentation enabled (including PreparedStatements)")
        except Exception as e:
            logger.warning("Failed to instrument AsyncPG", error=str(e))

        # Instrument HTTPX
        try:
            from opentelemetry.instrumentation.httpx import (  # type: ignore
                HTTPXClientInstrumentor,
            )

            HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)
        except Exception as e:
            logger.warning("Failed to instrument HTTPX", error=str(e))

        logger.info("OpenTelemetry instrumentation enabled")
    except Exception as e:
        logger.error("Failed to initialize OpenTelemetry", error=str(e))
