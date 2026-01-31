"""
Database connection management
"""

import os
import threading
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)

# Global shared connection pools (proper FastAPI pattern)
_engine = None
_session_local = None
_sync_initialized = False
_sync_init_lock = threading.Lock()


class AsyncDBContext(threading.local):
    engine: AsyncEngine | None
    initialized: bool
    session_local: async_sessionmaker[AsyncSession] | None
    lock: threading.Lock

    def __init__(self):
        self.engine = None
        self.initialized = False
        self.session_local = None
        self.lock = threading.Lock()  # Per-thread lock for async initialization


_async_db_ctx = AsyncDBContext()


def get_database_url() -> str:
    """Get database URL, checking environment variables first for test compatibility."""
    # Always check environment first (for tests), then fall back to settings
    db_url = os.getenv("BOARDS_DATABASE_URL")
    if not db_url:
        # For tests that set env vars after settings are loaded
        if "BOARDS_DATABASE_URL" in os.environ:
            db_url = os.environ["BOARDS_DATABASE_URL"]
        else:
            db_url = settings.database_url
    return db_url


def reset_database():
    """Reset database connections (for tests)."""
    global _engine, _session_local, _sync_initialized

    # Dispose of sync engine if it exists
    if _engine is not None:
        _engine.dispose()

    _engine = None
    _session_local = None
    _sync_initialized = False

    # Reset async context for current thread
    # Note: async engine disposal must be done with await, so we just clear the reference
    # The engine will be garbage collected when no sessions reference it
    _async_db_ctx.engine = None
    _async_db_ctx.session_local = None
    _async_db_ctx.initialized = False


async def test_database_connection() -> tuple[bool, str | None]:
    """
    Test the database connection and return helpful error messages.

    Returns:
        tuple: (success: bool, error_message: str | None)
    """
    if _async_db_ctx.engine is None:
        return False, "Database engine not initialized"

    try:
        async with _async_db_ctx.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True, None
    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__

        # Provide helpful error messages based on the error type
        if "does not exist" in error_str and "role" in error_str:
            # This is the confusing error - could be database server not running
            db_url = get_database_url()
            # Extract database name from URL
            db_name = db_url.split("/")[-1].split("?")[0]
            return False, (
                f"Cannot connect to database: {error_str}\n"
                f"This usually means:\n"
                f"  1. The database server is not running\n"
                f"  2. The database '{db_name}' doesn't exist\n"
                f"  3. The database user/role doesn't exist\n"
                f"Please check your database connection and run migrations if needed."
            )
        elif "Connection refused" in error_str or "could not connect" in error_str:
            return False, (
                f"Cannot connect to database server: {error_str}\n"
                f"The database server appears to be down or unreachable.\n"
                f"Please check that PostgreSQL is running and accessible."
            )
        elif "password authentication failed" in error_str:
            return False, (
                f"Database authentication failed: {error_str}\n"
                f"Please check your database credentials."
            )
        else:
            return False, f"Database connection error ({error_type}): {error_str}"


def init_database(database_url: str | None = None, force_reinit: bool = False):
    """Initialize shared database connection pools.

    Thread-safe initialization using a lock to prevent race conditions
    when multiple threads attempt to initialize simultaneously.
    """
    global _engine, _session_local, _sync_initialized

    # Get the database URL
    db_url = database_url or get_database_url()

    # Initialize Sync Engine (Global)
    if not _sync_initialized or force_reinit:
        with _sync_init_lock:
            if not _sync_initialized or force_reinit:
                sync_db_url = db_url
                if db_url.startswith("postgresql://"):
                    sync_db_url = db_url.replace("postgresql://", "postgresql+psycopg://")
                _engine = create_engine(
                    url=sync_db_url,
                    pool_size=settings.database_pool_size,
                    max_overflow=settings.database_max_overflow,
                    echo=settings.sql_echo,
                    # Supabase connection pooler can close idle connections
                    pool_pre_ping=True,
                    pool_recycle=300,
                )
                _session_local = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
                _sync_initialized = True

                # Instrument Sync Engine (production or local with OTEL enabled)
                is_production = settings.environment.lower() in ("production", "prod")
                is_local_otel = (
                    settings.environment.lower() not in ("production", "prod")
                    and settings.otel_enabled
                )
                if is_production or is_local_otel:
                    try:
                        tracer_provider = trace.get_tracer_provider()
                        SQLAlchemyInstrumentor().instrument(
                            engine=_engine, tracer_provider=tracer_provider
                        )
                    except Exception as e:
                        logger.warning("Failed to instrument sync engine", error=str(e))

                logger.info("Sync database initialized", database_url=db_url)

    # Initialize Async Engine (Thread-Local)
    # Async engines must be thread-local because asyncpg connections are tied to the event loop
    # and cannot be shared across threads/loops.
    if not _async_db_ctx.initialized or force_reinit:
        with _async_db_ctx.lock:
            # Double-check after acquiring lock (another coroutine may have initialized)
            if not _async_db_ctx.initialized or force_reinit:
                if db_url.startswith("postgresql://"):
                    async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
                    # Detect if using transaction pooling (pgbouncer/Supavisor)
                    is_transaction_pooling = "pgbouncer=true" in db_url or ":6543" in db_url

                    # Log URL without credentials
                    url_display = async_db_url.split("@")[1] if "@" in async_db_url else "hidden"

                    if is_transaction_pooling:
                        # Transaction pooling mode:
                        # - Use NullPool (no SQLAlchemy pooling, let pgbouncer handle it)
                        # - Disable prepared statements (pgbouncer doesn't support them)
                        # - Use both URL param and connect_args to ensure it's disabled
                        logger.info(
                            "Transaction pooling mode - using NullPool",
                            url=url_display,
                        )
                        _async_db_ctx.engine = create_async_engine(
                            url=async_db_url,
                            echo=settings.sql_echo,
                            poolclass=NullPool,
                            connect_args={
                                "statement_cache_size": 0,
                                # Use unnamed prepared statements for pgbouncer compatibility
                                # Empty string causes asyncpg to use unnamed statements
                                "prepared_statement_name_func": lambda: "",
                            },
                        )
                    else:
                        # Direct connection mode: use SQLAlchemy pooling
                        logger.info(
                            "Direct connection mode - using connection pool",
                            url=url_display,
                        )
                        _async_db_ctx.engine = create_async_engine(
                            url=async_db_url,
                            pool_size=settings.database_pool_size,
                            max_overflow=settings.database_max_overflow,
                            echo=settings.sql_echo,
                            pool_pre_ping=True,
                            pool_recycle=300,
                        )
                    _async_db_ctx.session_local = async_sessionmaker(
                        _async_db_ctx.engine,
                        class_=AsyncSession,
                        autocommit=False,
                        autoflush=False,
                    )
                    _async_db_ctx.initialized = True

                    # Instrument Async Engine (production or local with OTEL enabled)
                    is_production = settings.environment.lower() in ("production", "prod")
                    is_local_otel = (
                        settings.environment.lower() not in ("production", "prod")
                        and settings.otel_enabled
                    )
                    if is_production or is_local_otel:
                        try:
                            tracer_provider = trace.get_tracer_provider()
                            # For async engines, must instrument the underlying sync_engine
                            SQLAlchemyInstrumentor().instrument(
                                engine=_async_db_ctx.engine.sync_engine,
                                tracer_provider=tracer_provider,
                            )
                            logger.info("SQLAlchemy instrumentation enabled for async engine")
                        except Exception as e:
                            logger.warning("Failed to instrument async engine", error=str(e))

                    logger.info(
                        "Async database initialized for thread",
                        thread_id=threading.get_ident(),
                    )
                else:
                    logger.warning(
                        "Non-PostgreSQL URL detected, async engine not initialized",
                        url_prefix=(db_url.split("://")[0] if "://" in db_url else "unknown"),
                    )


def get_engine():
    """Get the shared SQLAlchemy engine."""
    if _engine is None:
        init_database()
    return _engine


def get_async_engine():
    """Get the shared async SQLAlchemy engine."""
    if _async_db_ctx.engine is None:
        init_database()
    return _async_db_ctx.engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session (sync) from shared pool."""
    if _session_local is None:
        init_database()

    if _session_local is None:
        raise RuntimeError("Database not initialized")

    session = _session_local()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session (async) from shared pool."""
    if _async_db_ctx.session_local is None:
        init_database()

    if _async_db_ctx.session_local is None:
        raise RuntimeError("Async database not available (PostgreSQL required)")

    async with _async_db_ctx.session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with get_async_session() as session:
        yield session


# Test-specific database session context
@asynccontextmanager
async def get_test_db_session(database_url: str) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for testing with explicit database URL."""
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from ..config import settings

    # Convert to async URL for PostgreSQL
    if database_url.startswith("postgresql://"):
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        async_url = database_url

    # Create isolated engine for this session
    engine = create_async_engine(
        async_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.debug,
        isolation_level="AUTOCOMMIT",  # Ensure we can see committed schema changes
    )

    session_local = async_sessionmaker(
        engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
    )

    async with session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await engine.dispose()
