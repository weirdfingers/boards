# Migration Runner Tests

This directory contains comprehensive tests for the database migration runner.

## Running Tests

### Prerequisites

Ensure you have:
- PostgreSQL running (configured via `DATABASE_URL` or settings)
- Required Python dependencies installed (`pytest`, `psycopg2-binary`)

### Test Commands

```bash
# Run all migration runner tests
python -m pytest tests/test_migration_runner.py -v

# Run fast tests only (skip slow/concurrent tests)
python -m pytest tests/test_migration_runner.py -m "not slow"

# Run only unit tests (no database required)
python -m pytest tests/test_migration_runner.py -m "unit"

# Run integration tests (requires database)
python -m pytest tests/test_migration_runner.py -m "integration"

# Run tests that require database connection
python -m pytest tests/test_migration_runner.py -m "requires_db"

# Run with coverage
python -m pytest tests/test_migration_runner.py --cov=migrations --cov-report=html

# Run specific test
python -m pytest tests/test_migration_runner.py::TestMigrationRunner::test_apply_single_migration -v
```

## Test Structure

### Test Classes

- **`TestMigrationRunner`**: Core migration functionality tests
  - Basic migration operations (up/down)
  - Transaction support and rollback
  - Error handling
  - Advisory locking
  - Checksum verification

- **`TestMigrationRunnerCommands`**: Command-line interface tests
  - Status, history, pending commands
  - Output formatting verification

- **`TestErrorScenarios`**: Error condition tests
  - Invalid database URLs
  - Connection failures
  - Missing migrations

### Test Markers

- `@pytest.mark.requires_db`: Tests that need database connection
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.slow`: Slow-running tests (e.g., concurrency tests)

### Fixtures

- `test_database`: Creates isolated test databases for each test
- `temp_migrations_dir`: Creates temporary directories for test migrations
- `migration_runner`: Configured MigrationRunner instance
- `db_connection`: Direct database connection for test setup

## Test Database Isolation

Each test function gets its own isolated PostgreSQL database that is:
- Created before the test runs
- Populated with test data as needed
- Completely destroyed after the test completes

This ensures no test interference and clean test environments.

## Writing New Tests

When adding new tests:

1. Use appropriate markers (`@pytest.mark.requires_db`, etc.)
2. Use the provided fixtures for consistency
3. Follow the existing test patterns
4. Add both positive and negative test cases
5. Test error conditions and edge cases

Example:

```python
@pytest.mark.requires_db
@pytest.mark.integration
class TestNewFeature:
    def test_new_functionality(self, migration_runner, temp_migrations_dir):
        # Create test migration files
        create_migration_files(temp_migrations_dir, "test_new_feature")
        
        # Test the functionality
        migration_runner.up()
        
        # Verify results
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 1
```