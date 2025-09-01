"""
Shared pytest fixtures and configuration for all tests.
"""

import os
import sys
import time
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path

# Add src directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.boards.config import settings


@pytest.fixture(scope="session")
def database_config():
    """Provide database configuration from settings."""
    # Parse database URL
    base_url = settings.database_url
    conn_str = base_url.replace("postgresql://", "")
    auth, host_db = conn_str.split("@", 1)
    host_port, db_name = host_db.split("/", 1) if "/" in host_db else (host_db, "postgres")
    user, password = auth.split(":", 1) if ":" in auth else (auth, "")
    
    # Extract host and port
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 5432
    
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": db_name
    }


@pytest.fixture(scope="function")
def test_database(database_config):
    """Create a test database for each test function."""
    # Create unique test database name
    test_db_name = f"test_{os.getpid()}_{int(time.time() * 1000)}"
    
    # Connect to postgres to create test database
    conn = psycopg2.connect(
        host=database_config["host"],
        port=database_config["port"],
        user=database_config["user"],
        password=database_config["password"],
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE {test_db_name}")
    cursor.close()
    conn.close()
    
    # Build test database URL
    test_url = (
        f"postgresql://{database_config['user']}:{database_config['password']}"
        f"@{database_config['host']}:{database_config['port']}/{test_db_name}"
    )
    
    yield test_url, test_db_name
    
    # Cleanup: drop test database
    conn = psycopg2.connect(
        host=database_config["host"],
        port=database_config["port"],
        user=database_config["user"],
        password=database_config["password"],
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    # Terminate any connections to the test database
    cursor.execute(f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{test_db_name}'
        AND pid <> pg_backend_pid()
    """)
    cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    cursor.close()
    conn.close()


@pytest.fixture(scope="function")
def db_connection(test_database):
    """Provide a database connection to the test database."""
    test_url, _ = test_database
    
    # Parse test database URL
    conn_str = test_url.replace("postgresql://", "")
    auth, host_db = conn_str.split("@", 1)
    host_port, db_name = host_db.split("/", 1)
    user, password = auth.split(":", 1) if ":" in auth else (auth, "")
    
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 5432
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name
    )
    
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
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring database connection"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )