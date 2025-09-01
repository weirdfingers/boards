"""
Database connection management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)

# Sync engine and session factory
engine = None
SessionLocal = None

# Async engine and session factory
async_engine = None
AsyncSessionLocal = None

def init_database(database_url: Optional[str] = None):
    """Initialize database connections."""
    global engine, SessionLocal, async_engine, AsyncSessionLocal
    
    db_url = database_url or settings.database_url
    
    # Create sync engine
    engine = create_engine(
        db_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.debug,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create async engine (if PostgreSQL)
    if db_url.startswith("postgresql://"):
        async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        async_engine = create_async_engine(
            async_db_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug,
        )
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
        )
    
    logger.info("Database initialized", database_url=db_url)

def get_engine():
    """Get the SQLAlchemy engine."""
    if engine is None:
        init_database()
    return engine

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session (sync)."""
    if SessionLocal is None:
        init_database()
    
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    session = SessionLocal()
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
    """Get a database session (async)."""
    if AsyncSessionLocal is None:
        init_database()
    
    if AsyncSessionLocal is None:
        raise RuntimeError("Async database not available (PostgreSQL required)")
    
    async with AsyncSessionLocal() as session:
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