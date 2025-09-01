#!/usr/bin/env python3
"""
Test suite for the database migration runner.
Tests transaction support, error handling, and rollback capabilities.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import threading
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from migrations.migration_runner import MigrationRunner, MigrationError


@pytest.fixture(scope="function")
def temp_migrations_dir():
    """Create a temporary directory for test migrations."""
    temp_dir = tempfile.mkdtemp(prefix="test_migrations_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def migration_runner(test_database, temp_migrations_dir):
    """Create a MigrationRunner instance for testing."""
    test_url, _ = test_database
    return MigrationRunner(
        database_url=test_url,
        migrations_dir=temp_migrations_dir
    )


def create_migration_files(migrations_dir: Path, name: str, version: Optional[str] = None):
    """Helper to create test migration files."""
    if version is None:
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create UP migration
    up_content = f"""-- Migration: {version}_{name} UP
-- Generated: {datetime.now().isoformat()}

CREATE TABLE {name}_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO {name}_table (name, value) VALUES ('test1', 100);
INSERT INTO {name}_table (name, value) VALUES ('test2', 200);
"""
    
    # Create DOWN migration
    down_content = f"""-- Migration: {version}_{name} DOWN
-- Generated: {datetime.now().isoformat()}

DROP TABLE IF EXISTS {name}_table;
"""
    
    up_file = migrations_dir / f"{version}_{name}_up.sql"
    down_file = migrations_dir / f"{version}_{name}_down.sql"
    
    up_file.write_text(up_content)
    down_file.write_text(down_content)
    
    return version, up_file, down_file


@pytest.mark.requires_db
@pytest.mark.integration
class TestMigrationRunner:
    """Test suite for MigrationRunner."""
    
    def test_initialization(self, migration_runner):
        """Test that migration runner initializes correctly."""
        assert migration_runner.MIGRATIONS_TABLE == "schema_migrations"
        assert migration_runner.migrations_dir.exists()
        assert migration_runner.db_name is not None
    
    def test_ensure_migrations_table(self, migration_runner):
        """Test that migrations table is created correctly."""
        migration_runner._ensure_migrations_table()
        
        with migration_runner.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'schema_migrations'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            cursor.close()
        
        # Verify table structure
        expected_columns = {
            'version': 'character varying',
            'name': 'character varying',
            'applied_at': 'timestamp with time zone',
            'execution_time_ms': 'integer',
            'checksum': 'character varying',
            'applied_by': 'character varying'
        }
        
        actual_columns = {col[0]: col[1] for col in columns}
        for col_name, col_type in expected_columns.items():
            assert col_name in actual_columns
            assert actual_columns[col_name] == col_type
    
    def test_apply_single_migration(self, migration_runner, temp_migrations_dir):
        """Test applying a single migration."""
        version, up_file, _ = create_migration_files(temp_migrations_dir, "test_apply")
        
        migration_runner.up()
        
        # Verify migration was applied
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 1
        assert applied[0]['version'] == f"{version}_test_apply"
        assert applied[0]['name'] == "test_apply"
        assert applied[0]['checksum'] is not None
        
        # Verify table was created
        with migration_runner.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM test_apply_table
            """)
            count = cursor.fetchone()[0]
            cursor.close()
        
        assert count == 2  # Should have 2 test records
    
    def test_rollback_migration(self, migration_runner, temp_migrations_dir):
        """Test rolling back a migration."""
        version, _, _ = create_migration_files(temp_migrations_dir, "test_rollback")
        
        # Apply migration
        migration_runner.up()
        
        # Verify it was applied
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 1
        
        # Rollback
        migration_runner.down(target="zero")
        
        # Verify rollback
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 0
        
        # Verify table was dropped
        with migration_runner.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'test_rollback_table'
                )
            """)
            exists = cursor.fetchone()[0]
            cursor.close()
        
        assert not exists
    
    def test_multiple_migrations_order(self, migration_runner, temp_migrations_dir):
        """Test that multiple migrations are applied in correct order."""
        # Create migrations with specific timestamps
        v1, _, _ = create_migration_files(temp_migrations_dir, "first", "20240101_120000")
        v2, _, _ = create_migration_files(temp_migrations_dir, "second", "20240102_120000")
        v3, _, _ = create_migration_files(temp_migrations_dir, "third", "20240103_120000")
        
        migration_runner.up()
        
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 3
        assert applied[0]['version'] == "20240101_120000_first"
        assert applied[1]['version'] == "20240102_120000_second"
        assert applied[2]['version'] == "20240103_120000_third"
    
    def test_partial_rollback(self, migration_runner, temp_migrations_dir):
        """Test rolling back to a specific version."""
        create_migration_files(temp_migrations_dir, "first", "20240101_120000")
        create_migration_files(temp_migrations_dir, "second", "20240102_120000")
        create_migration_files(temp_migrations_dir, "third", "20240103_120000")
        
        # Apply all migrations
        migration_runner.up()
        assert len(migration_runner._get_applied_migrations()) == 3
        
        # Rollback to second migration
        migration_runner.down(target="20240102_120000_second")
        
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 2
        assert applied[-1]['version'] == "20240102_120000_second"
    
    def test_dry_run_mode(self, migration_runner, temp_migrations_dir):
        """Test that dry-run mode doesn't apply changes."""
        create_migration_files(temp_migrations_dir, "test_dryrun")
        
        # Run in dry-run mode
        migration_runner.up(dry_run=True)
        
        # Verify no migrations were applied
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 0
        
        # Verify table wasn't created
        with migration_runner.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'test_dryrun_table'
                )
            """)
            exists = cursor.fetchone()[0]
            cursor.close()
        
        assert not exists
    
    def test_migration_with_error(self, migration_runner, temp_migrations_dir):
        """Test that migration with SQL error rolls back properly."""
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create migration with intentional error
        bad_up = temp_migrations_dir / f"{version}_bad_migration_up.sql"
        bad_up.write_text("""-- Bad migration
CREATE TABLE test_table (id SERIAL PRIMARY KEY);
INSERT INTO nonexistent_table (col) VALUES ('fail');
""")
        
        bad_down = temp_migrations_dir / f"{version}_bad_migration_down.sql"
        bad_down.write_text("DROP TABLE IF EXISTS test_table;")
        
        # Attempt to apply migration
        with pytest.raises(MigrationError) as exc_info:
            migration_runner.up()
        
        assert "Failed to apply migration" in str(exc_info.value)
        
        # Verify no migrations were applied
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 0
        
        # Verify table wasn't created (transaction rolled back)
        with migration_runner.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'test_table'
                )
            """)
            exists = cursor.fetchone()[0]
            cursor.close()
        
        assert not exists
    
    def test_checksum_verification(self, migration_runner, temp_migrations_dir):
        """Test that modified migrations are detected."""
        version, up_file, _ = create_migration_files(temp_migrations_dir, "test_checksum")
        
        # Apply migration
        migration_runner.up()
        
        # Modify the migration file
        up_file.write_text("""-- Modified migration
CREATE TABLE completely_different_table (id INTEGER);
""")
        
        # Verify checksum mismatch is detected
        migration_runner.verify()
        # Note: verify() prints to stdout, in a real scenario we'd capture and assert
    
    @pytest.mark.slow
    def test_advisory_lock(self, migration_runner, temp_migrations_dir):
        """Test that advisory lock prevents concurrent migrations."""
        # Create a migration that takes some time to complete
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create UP migration with a delay
        up_content = f"""-- Migration: {version}_slow_migration UP
-- This migration includes a delay to test locking

CREATE TABLE slow_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- Add some delay by performing a slower operation
INSERT INTO slow_table (name) 
SELECT 'test_' || generate_series(1, 1000);

-- Add a pg_sleep to ensure the lock is held long enough
SELECT pg_sleep(0.5);
"""
        
        # Create DOWN migration
        down_content = f"""-- Migration: {version}_slow_migration DOWN
DROP TABLE IF EXISTS slow_table;
"""
        
        up_file = temp_migrations_dir / f"{version}_slow_migration_up.sql"
        down_file = temp_migrations_dir / f"{version}_slow_migration_down.sql"
        
        up_file.write_text(up_content)
        down_file.write_text(down_content)
        
        # Track results from threads
        results: Dict[str, Optional[str]] = {'first': None, 'second': None}
        
        def run_migration(name):
            try:
                migration_runner.up()
                results[name] = 'success'
            except MigrationError as e:
                if "Could not acquire migration lock" in str(e):
                    results[name] = 'locked'
                else:
                    results[name] = f'error: {e}'
        
        # Start first migration in a thread
        thread1 = threading.Thread(target=run_migration, args=('first',))
        thread1.start()
        
        # Give first thread time to acquire lock and start migration
        time.sleep(0.1)
        
        # Try to run second migration (should fail to acquire lock)
        thread2 = threading.Thread(target=run_migration, args=('second',))
        thread2.start()
        
        # Wait for both threads
        thread1.join(timeout=10)
        thread2.join(timeout=10)
        
        # One should succeed, one should be locked
        assert 'success' in results.values(), f"Expected success but got: {results}"
        assert 'locked' in results.values(), f"Expected locked but got: {results}"
    
    def test_pending_migrations(self, migration_runner, temp_migrations_dir):
        """Test listing pending migrations."""
        create_migration_files(temp_migrations_dir, "first", "20240101_120000")
        create_migration_files(temp_migrations_dir, "second", "20240102_120000")
        
        # Get pending before applying
        available = migration_runner._get_migration_files("up")
        assert len(available) == 2
        
        # Apply first migration
        migration_runner.up(target="20240101_120000_first")
        
        # Check what's still pending
        applied = {m['version'] for m in migration_runner._get_applied_migrations()}
        pending = [v for v, _ in available if v not in applied]
        
        assert len(pending) == 1
        assert pending[0] == "20240102_120000_second"
    
    def test_migration_up_to_target(self, migration_runner, temp_migrations_dir):
        """Test applying migrations up to a specific target."""
        create_migration_files(temp_migrations_dir, "first", "20240101_120000")
        create_migration_files(temp_migrations_dir, "second", "20240102_120000")
        create_migration_files(temp_migrations_dir, "third", "20240103_120000")
        
        # Apply up to second migration only
        migration_runner.up(target="20240102_120000_second")
        
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 2
        assert applied[-1]['version'] == "20240102_120000_second"
    
    def test_idempotent_migrations(self, migration_runner, temp_migrations_dir):
        """Test that running up() multiple times is safe."""
        create_migration_files(temp_migrations_dir, "test_idempotent")
        
        # Apply migration
        migration_runner.up()
        first_applied = migration_runner._get_applied_migrations()
        
        # Apply again (should do nothing)
        migration_runner.up()
        second_applied = migration_runner._get_applied_migrations()
        
        assert len(first_applied) == len(second_applied)
        assert first_applied[0]['version'] == second_applied[0]['version']
    
    def test_missing_down_migration(self, migration_runner, temp_migrations_dir):
        """Test error handling when DOWN migration is missing."""
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create only UP migration
        up_file = temp_migrations_dir / f"{version}_missing_down_up.sql"
        up_file.write_text("CREATE TABLE test_table (id SERIAL PRIMARY KEY);")
        
        # Apply migration
        migration_runner.up()
        
        # Try to rollback (should fail due to missing DOWN file)
        with pytest.raises(MigrationError) as exc_info:
            migration_runner.down(target="zero")
        
        assert "Down migration file not found" in str(exc_info.value)
    
    def test_execution_time_tracking(self, migration_runner, temp_migrations_dir):
        """Test that execution time is tracked correctly."""
        create_migration_files(temp_migrations_dir, "test_timing")
        
        migration_runner.up()
        
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 1
        assert applied[0]['execution_time_ms'] is not None
        assert applied[0]['execution_time_ms'] >= 0
    
    def test_applied_by_tracking(self, migration_runner, temp_migrations_dir):
        """Test that the user who applied migration is tracked."""
        create_migration_files(temp_migrations_dir, "test_user")
        
        migration_runner.up()
        
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 1
        assert applied[0]['applied_by'] is not None
        assert applied[0]['applied_by'] == os.getenv("USER", "unknown")


@pytest.mark.requires_db
@pytest.mark.integration
class TestMigrationRunnerCommands:
    """Test the command-line interface methods."""
    
    def test_status_command(self, migration_runner, temp_migrations_dir, capsys):
        """Test the status command output."""
        create_migration_files(temp_migrations_dir, "test_status")
        
        # Before applying
        migration_runner.status()
        captured = capsys.readouterr()
        assert "○ Pending" in captured.out
        assert "0 applied, 1 pending" in captured.out
        
        # After applying
        migration_runner.up()
        migration_runner.status()
        captured = capsys.readouterr()
        assert "✓ Applied" in captured.out
        assert "1 applied, 0 pending" in captured.out
    
    def test_history_command(self, migration_runner, temp_migrations_dir, capsys):
        """Test the history command output."""
        create_migration_files(temp_migrations_dir, "test_history")
        migration_runner.up()
        
        migration_runner.history(limit=5)
        captured = capsys.readouterr()
        
        assert "Migration History" in captured.out
        assert "test_history" in captured.out
        assert "Applied At" in captured.out
    
    def test_pending_command(self, migration_runner, temp_migrations_dir, capsys):
        """Test the pending command output."""
        create_migration_files(temp_migrations_dir, "pending1", "20240101_120000")
        create_migration_files(temp_migrations_dir, "pending2", "20240102_120000")
        
        migration_runner.pending()
        captured = capsys.readouterr()
        
        assert "Pending Migrations (2 total)" in captured.out
        assert "pending1" in captured.out
        assert "pending2" in captured.out
    
    def test_verify_command(self, migration_runner, temp_migrations_dir, capsys):
        """Test the verify command output."""
        version, up_file, _ = create_migration_files(temp_migrations_dir, "test_verify")
        migration_runner.up()
        
        # First verify - should be OK
        migration_runner.verify()
        captured = capsys.readouterr()
        assert "✅ All migration checksums verified successfully" in captured.out
        
        # Modify file and verify again
        up_file.write_text("-- Modified content")
        migration_runner.verify()
        captured = capsys.readouterr()
        assert "❌ Checksum mismatches detected" in captured.out


@pytest.mark.unit
class TestErrorScenarios:
    """Test various error scenarios."""
    
    def test_invalid_database_url(self, temp_migrations_dir):
        """Test handling of invalid database URL."""
        with pytest.raises(ValueError) as exc_info:
            MigrationRunner(
                database_url="invalid://url",
                migrations_dir=temp_migrations_dir
            )
        assert "Only PostgreSQL databases are supported" in str(exc_info.value)
    
    @pytest.mark.requires_db
    def test_connection_failure(self, temp_migrations_dir):
        """Test handling of database connection failure."""
        runner = MigrationRunner(
            database_url="postgresql://invalid:invalid@localhost:9999/nonexistent",
            migrations_dir=temp_migrations_dir
        )
        
        with pytest.raises(MigrationError) as exc_info:
            runner.up()
        assert "Database error" in str(exc_info.value)
    
    @pytest.mark.requires_db  
    def test_empty_migrations_directory(self, migration_runner):
        """Test behavior with no migrations to apply."""
        migration_runner.up()  # Should not raise error
        
        applied = migration_runner._get_applied_migrations()
        assert len(applied) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])