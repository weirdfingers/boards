"""
Database connection management
"""

import os
import threading
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)

# Global shared connection pools (proper FastAPI pattern)
_engine = None
_async_engine = None
_session_local = None
_async_session_local = None
_initialized = False
_init_lock = threading.Lock()  # Protect initialization from race conditions


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
    global _engine, _async_engine, _session_local, _async_session_local, _initialized
    _engine = None
    _async_engine = None
    _session_local = None
    _async_session_local = None
    _initialized = False


async def test_database_connection() -> tuple[bool, str | None]:
    """
    Test the database connection and return helpful error messages.

    Returns:
        tuple: (success: bool, error_message: str | None)
    """
    if _async_engine is None:
        return False, "Database engine not initialized"

    try:
        async with _async_engine.connect() as conn:
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
    global _engine, _async_engine, _session_local, _async_session_local, _initialized

    # Fast path: already initialized, no lock needed
    if _initialized and not force_reinit and database_url is None:
        return

    # Slow path: acquire lock for initialization
    with _init_lock:
        # Double-check after acquiring lock (another thread may have initialized)
        if _initialized and not force_reinit and database_url is None:
            return

        # Get the database URL
        db_url = database_url or get_database_url()

        # Create sync engine
        _engine = create_engine(
            db_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.sql_echo,
        )
        _session_local = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

        # Create async engine (if PostgreSQL)
        if db_url.startswith("postgresql://"):
            async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            _async_engine = create_async_engine(
                async_db_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                echo=settings.sql_echo,
            )
            _async_session_local = async_sessionmaker(
                _async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
            )

        _initialized = True
        logger.info("Database initialized", database_url=db_url)


def get_engine():
    """Get the shared SQLAlchemy engine."""
    if _engine is None:
        init_database()
    return _engine


def get_async_engine():
    """Get the shared async SQLAlchemy engine."""
    if _async_engine is None:
        init_database()
    return _async_engine


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
    if _async_session_local is None:
        init_database()

    if _async_session_local is None:
        raise RuntimeError("Async database not available (PostgreSQL required)")

    async with _async_session_local() as session:
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
