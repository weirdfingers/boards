from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context  # type: ignore[reportMissingImports]

# Ensure backend src/ is on sys.path so imports work when running Alembic
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from boards.config import settings  # type: ignore
from boards.dbmodels import target_metadata  # type: ignore

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_sync_url() -> str:
    # Use the same logic as get_database_url() from the application
    # Check environment variables first, then fall back to settings
    import os

    db_url = os.getenv("BOARDS_DATABASE_URL")
    if not db_url:
        # For tests that set env vars after settings are loaded
        if "BOARDS_DATABASE_URL" in os.environ:
            db_url = os.environ["BOARDS_DATABASE_URL"]
        else:
            db_url = settings.database_url
    return db_url


def get_async_url() -> str:
    url = get_sync_url()
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    sync_url = get_sync_url()
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode with AsyncEngine.
    """
    connectable: AsyncEngine = create_async_engine(
        get_async_url(), poolclass=pool.NullPool
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
