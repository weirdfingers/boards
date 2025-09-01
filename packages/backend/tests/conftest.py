"""
Shared pytest fixtures and configuration for all tests.
"""

import os
import sys
import pytest
from pathlib import Path
from typing import Any, Generator, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    # Import types only for type checking, not at runtime
    from pytest_postgresql.executor import PostgreSQLExecutor  # type: ignore[import]
    from psycopg import Connection  # type: ignore[import]
else:
    # Runtime fallbacks
    PostgreSQLExecutor = Any
    Connection = Any

# Add src directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command


@pytest.fixture(scope="function", autouse=False)
def alembic_migrate(
    postgresql_proc: PostgreSQLExecutor, postgresql: Connection[Any]
) -> Generator[None, None, None]:
    """Run Alembic upgrade to head against the pytest-postgresql instance."""
    dsn = (
        f"postgresql://{postgresql.user}:{postgresql.password}"  # type: ignore[reportUnknownMemberType]
        f"@{postgresql.host}:{postgresql.port}/{postgresql.dbname}"  # type: ignore[reportUnknownMemberType]
    )

    os.environ["BOARDS_DATABASE_URL"] = dsn
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(scope="function")
def test_database(
    postgresql: Connection[Any],
) -> Generator[Tuple[str, str], None, None]:
    """Return the DSN for the running pytest-postgresql database."""
    dsn = (
        f"postgresql://{postgresql.user}:{postgresql.password}"  # type: ignore[reportUnknownMemberType]
        f"@{postgresql.host}:{postgresql.port}/{postgresql.dbname}"  # type: ignore[reportUnknownMemberType]
    )
    yield dsn, postgresql.dbname  # type: ignore[reportUnknownMemberType]


@pytest.fixture(scope="function")
def db_connection(
    postgresql: Connection[Any],
) -> Generator[Connection[Any], None, None]:
    """Provide a psycopg2 connection via pytest-postgresql (if needed by tests)."""
    conn = postgresql.cursor().connection
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def reset_environment() -> Generator[None, None, None]:
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


# Test markers
def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(  # type: ignore[reportUnknownMemberType]
        "markers", "requires_db: mark test as requiring database connection"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")  # type: ignore[reportUnknownMemberType]
    config.addinivalue_line("markers", "integration: mark test as integration test")  # type: ignore[reportUnknownMemberType]
    config.addinivalue_line("markers", "unit: mark test as unit test")  # type: ignore[reportUnknownMemberType]
