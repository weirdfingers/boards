"""
Shared pytest fixtures and configuration for all tests.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config  # type: ignore[reportMissingImports]
from alembic import command  # type: ignore[reportMissingImports]


@pytest.fixture(scope="function", autouse=False)
def alembic_migrate(postgresql_proc, postgresql):  # type: ignore[reportUnknownParameterType]
    """Run Alembic upgrade to head against the pytest-postgresql instance."""
    dsn = (
        f"postgresql://{postgresql.user}:{postgresql.password}"
        f"@{postgresql.host}:{postgresql.port}/{postgresql.dbname}"
    )
    os.environ["BOARDS_DATABASE_URL"] = dsn
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(scope="function")
def test_database(postgresql):  # type: ignore[reportUnknownParameterType]
    """Return the DSN for the running pytest-postgresql database."""
    dsn = (
        f"postgresql://{postgresql.user}:{postgresql.password}"
        f"@{postgresql.host}:{postgresql.port}/{postgresql.dbname}"
    )
    yield dsn, postgresql.dbname


@pytest.fixture(scope="function")
def db_connection(postgresql):  # type: ignore[reportUnknownParameterType]
    """Provide a psycopg2 connection via pytest-postgresql (if needed by tests)."""
    conn = postgresql.cursor().connection
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


# Test markers
def pytest_configure(config):  # type: ignore[reportUnknownParameterType]
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring database connection"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
