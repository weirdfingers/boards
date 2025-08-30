"""
Main FastAPI application for Boards backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from ..config import settings
from ..database import init_database
from ..graphql.schema import create_graphql_router

logger = logging.getLogger(__name__)

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
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}
    
    # GraphQL endpoint
    graphql_router = create_graphql_router()
    app.include_router(graphql_router, prefix="")
    
    # REST API endpoints (for SSE, webhooks, etc.)
    from .endpoints import sse, webhooks, storage
    
    app.include_router(sse.router, prefix="/api/sse", tags=["SSE"])
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