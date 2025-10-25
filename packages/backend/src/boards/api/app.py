"""
Main FastAPI application for Boards backend
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import initialize_generator_api_keys, settings
from ..database import init_database
from ..generators.loader import load_generators_from_config
from ..logging import configure_logging, get_logger
from ..middleware import LoggingContextMiddleware, TenantRoutingMiddleware

# Configure logging before creating logger
configure_logging(debug=settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Boards API...")
    init_database()
    logger.info("Database initialized")

    # Initialize generator API keys from settings
    initialize_generator_api_keys()
    logger.info("Generator API keys initialized")

    # Load generators based on configuration
    try:
        load_generators_from_config()
        logger.info(
            "Generators configured and registered",
            names=list(
                __import__(
                    "boards.generators.registry", fromlist=["registry"]
                ).registry.list_names()
            ),
        )
    except Exception as e:
        # Fail fast: strict mode default may raise here
        logger.error("Failed to configure generators", error=str(e))
        raise

    # Run comprehensive startup validation
    try:
        from ..validation import (
            ValidationError,
            get_startup_recommendations,
            validate_startup_configuration,
        )

        validation_results = await validate_startup_configuration()

        if not validation_results["overall_valid"]:
            # Log detailed error information
            logger.error(
                "Application configuration validation failed - some features may not work properly",
                database_errors=validation_results.get("database", {}).get("errors", []),
                tenant_errors=validation_results["tenant"].get("errors", []),
                auth_errors=validation_results["auth"].get("errors", []),
            )

            # In production, we might want to fail hard here
            if settings.environment.lower() in ("production", "prod"):
                raise ValidationError("Critical configuration validation failed in production")

        # Log recommendations
        recommendations = get_startup_recommendations(validation_results)
        if recommendations:
            logger.info("Configuration recommendations", recommendations=recommendations)

    except ValidationError:
        # Re-raise validation errors to fail startup
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during startup validation",
            error=str(e),
            note="Application will continue but may have configuration issues",
        )

    yield

    # Shutdown
    logger.info("Shutting down Boards API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Boards API",
        description="Open-source creative toolkit for AI-generated content",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Add tenant routing middleware first (runs before logging)
    app.add_middleware(TenantRoutingMiddleware)

    # Add logging context middleware
    app.add_middleware(LoggingContextMiddleware)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():  # pyright: ignore [reportUnusedFunction]
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    # GraphQL endpoint (allow disabling for tests)
    if not os.getenv("BOARDS_DISABLE_GRAPHQL"):
        try:
            from ..graphql.schema import create_graphql_router, validate_schema

            # Validate schema at startup to catch circular reference errors early
            logger.info("Validating GraphQL schema...")
            validate_schema()

            # Create and mount the GraphQL router
            graphql_router = create_graphql_router()
            app.include_router(graphql_router, prefix="")
            logger.info("GraphQL endpoint initialized successfully", endpoint="/graphql")
        except Exception as e:  # pragma: no cover
            logger.error("Failed to initialize GraphQL endpoint", error=str(e))
            # Re-raise to fail fast - server should not start with broken GraphQL
            raise

    # REST API endpoints (for SSE, webhooks, etc.)
    from .endpoints import jobs, setup, sse, storage, tenant_registration, webhooks

    app.include_router(sse.router, prefix="/api/sse", tags=["SSE"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
    app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
    app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
    app.include_router(setup.router, prefix="/api/setup", tags=["Setup"])
    app.include_router(
        tenant_registration.router, prefix="/api/tenants", tags=["Tenant Registration"]
    )

    return app


# Create the main application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "boards.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
