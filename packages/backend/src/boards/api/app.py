"""
Main FastAPI application for Boards backend
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..database import init_database
from ..logging import configure_logging, get_logger
from ..middleware import LoggingContextMiddleware

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

    # Add logging context middleware first
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
            from ..graphql.schema import create_graphql_router

            graphql_router = create_graphql_router()
            app.include_router(graphql_router, prefix="")
        except Exception as e:  # pragma: no cover
            logger.warning("Skipping GraphQL setup", error=str(e))

    # REST API endpoints (for SSE, webhooks, etc.)
    from .endpoints import jobs, sse, storage, webhooks

    app.include_router(sse.router, prefix="/api/sse", tags=["SSE"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
    app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
    app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])

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
