#!/usr/bin/env python3
"""
Database migration runner with transaction support and error handling.
Tracks applied migrations and provides rollback capabilities.
"""

import os
import sys
import hashlib
import argparse
import logging
import time
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_SERIALIZABLE

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.boards.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Base exception for migration errors."""
    pass


class MigrationRunner:
    """Handles database migrations with transaction support."""
    
    MIGRATIONS_TABLE = "schema_migrations"
    LOCK_ID = 742  # Arbitrary number for advisory lock
    
    def _format_table(self, data: List[List], headers: List[str]) -> str:
        """Format data as a simple ASCII table.
        
        Args:
            data: Table data as list of rows
            headers: Column headers
            
        Returns:
            Formatted table string
        """
        if not data:
            return "No data"
        
        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in data:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        
        # Build separator
        separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
        
        # Build header
        header_row = "|" + "|".join(f" {h:<{w}} " for h, w in zip(headers, widths)) + "|"
        
        # Build data rows
        rows = []
        for row in data:
            row_str = "|" + "|".join(f" {str(cell):<{w}} " for cell, w in zip(row, widths)) + "|"
            rows.append(row_str)
        
        # Combine all parts
        result = [separator, header_row, separator]
        result.extend(rows)
        result.append(separator)
        
        return "\n".join(result)
    
    def __init__(self, database_url: Optional[str] = None, migrations_dir: Optional[Path] = None):
        """Initialize migration runner.
        
        Args:
            database_url: Database connection URL
            migrations_dir: Directory containing migration files
        """
        self.database_url = database_url or settings.database_url
        self.migrations_dir = migrations_dir or Path(__file__).parent / "generated"
        
        # Parse database URL for connection
        self._parse_database_url()
        
    def _parse_database_url(self):
        """Parse database URL into connection parameters."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "")
        else:
            raise ValueError("Only PostgreSQL databases are supported")
        
        # Extract auth and host
        if "@" in url:
            auth, host_db = url.split("@", 1)
            if "/" in host_db:
                host_port, self.db_name = host_db.split("/", 1)
            else:
                host_port, self.db_name = host_db, "postgres"
        else:
            raise ValueError("Invalid database URL format")
        
        # Extract user and password
        if ":" in auth:
            self.db_user, self.db_password = auth.split(":", 1)
        else:
            self.db_user, self.db_password = auth, ""
        
        # Extract host and port
        if ":" in host_port:
            self.db_host, port_str = host_port.split(":", 1)
            self.db_port = int(port_str)
        else:
            self.db_host = host_port
            self.db_port = 5432
    
    @contextmanager
    def get_connection(self, autocommit: bool = False):
        """Get database connection with optional autocommit.
        
        Args:
            autocommit: Whether to use autocommit mode
            
        Yields:
            psycopg2 connection object
        """
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            
            if autocommit:
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            else:
                conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            
            yield conn
            
            if not autocommit:
                conn.commit()
                
        except psycopg2.Error as e:
            if conn and not autocommit:
                conn.rollback()
            raise MigrationError(f"Database error: {e}")
        finally:
            if conn:
                conn.close()
    
    def _acquire_lock(self, conn) -> bool:
        """Acquire advisory lock to prevent concurrent migrations.
        
        Args:
            conn: Database connection
            
        Returns:
            True if lock acquired, False otherwise
        """
        cursor = conn.cursor()
        cursor.execute("SELECT pg_try_advisory_lock(%s)", (self.LOCK_ID,))
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else False
    
    def _release_lock(self, conn):
        """Release advisory lock.
        
        Args:
            conn: Database connection
        """
        cursor = conn.cursor()
        cursor.execute("SELECT pg_advisory_unlock(%s)", (self.LOCK_ID,))
        cursor.close()
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        with self.get_connection(autocommit=True) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    checksum VARCHAR(64),
                    applied_by VARCHAR(255)
                )
            """)
            cursor.close()
            logger.info(f"Ensured {self.MIGRATIONS_TABLE} table exists")
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of migration content.
        
        Args:
            content: Migration SQL content
            
        Returns:
            Hex string of checksum
        """
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_applied_migrations(self) -> List[dict]:
        """Get list of applied migrations.
        
        Returns:
            List of migration records
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT version, name, applied_at, execution_time_ms, checksum, applied_by
                FROM schema_migrations
                ORDER BY version
            """)
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def _get_migration_files(self, direction: str = "up") -> List[Tuple[str, Path]]:
        """Get sorted list of migration files.
        
        Args:
            direction: 'up' or 'down'
            
        Returns:
            List of (version, filepath) tuples
        """
        pattern = f"*_{direction}.sql"
        files = sorted(self.migrations_dir.glob(pattern))
        
        migrations = []
        for filepath in files:
            # Extract version from filename (e.g., "20240830_143022_add_user_preferences")
            filename = filepath.stem  # Remove .sql
            if filename.endswith(f"_{direction}"):
                version = filename[:-len(f"_{direction}")]
                migrations.append((version, filepath))
        
        return migrations
    
    def _apply_migration(self, conn, filepath: Path, version: str, name: str, 
                        dry_run: bool = False) -> Optional[int]:
        """Apply a single migration file.
        
        Args:
            conn: Database connection
            filepath: Path to migration file
            version: Migration version
            name: Migration name
            dry_run: If True, don't actually apply
            
        Returns:
            Execution time in milliseconds, or None if dry run
        """
        with open(filepath) as f:
            content = f.read()
        
        if dry_run:
            logger.info(f"[DRY RUN] Would apply migration {version}: {name}")
            logger.debug(f"[DRY RUN] SQL:\n{content[:500]}...")
            return None
        
        checksum = self._calculate_checksum(content)
        start_time = time.time()
        
        cursor = conn.cursor()
        try:
            # Execute migration
            cursor.execute(content)
            
            # Record in migrations table
            execution_time_ms = int((time.time() - start_time) * 1000)
            cursor.execute("""
                INSERT INTO schema_migrations (version, name, execution_time_ms, checksum, applied_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (version, name, execution_time_ms, checksum, os.getenv("USER", "unknown")))
            
            logger.info(f"✓ Applied migration {version}: {name} ({execution_time_ms}ms)")
            return execution_time_ms
            
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to apply migration {version}: {e}")
        finally:
            cursor.close()
    
    def _rollback_migration(self, conn, filepath: Path, version: str, name: str,
                           dry_run: bool = False) -> Optional[int]:
        """Rollback a single migration.
        
        Args:
            conn: Database connection
            filepath: Path to down migration file
            version: Migration version
            name: Migration name
            dry_run: If True, don't actually rollback
            
        Returns:
            Execution time in milliseconds, or None if dry run
        """
        with open(filepath) as f:
            content = f.read()
        
        if dry_run:
            logger.info(f"[DRY RUN] Would rollback migration {version}: {name}")
            logger.debug(f"[DRY RUN] SQL:\n{content[:500]}...")
            return None
        
        start_time = time.time()
        
        cursor = conn.cursor()
        try:
            # Execute rollback
            cursor.execute(content)
            
            # Remove from migrations table
            cursor.execute("""
                DELETE FROM schema_migrations WHERE version = %s
            """, (version,))
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"✓ Rolled back migration {version}: {name} ({execution_time_ms}ms)")
            return execution_time_ms
            
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to rollback migration {version}: {e}")
        finally:
            cursor.close()
    
    def up(self, target: Optional[str] = None, dry_run: bool = False):
        """Apply pending migrations up to target version.
        
        Args:
            target: Target migration version (None for all)
            dry_run: If True, show what would be done without applying
        """
        self._ensure_migrations_table()
        
        with self.get_connection(autocommit=False) as conn:
            # Acquire lock
            if not self._acquire_lock(conn):
                raise MigrationError("Could not acquire migration lock. Another migration may be in progress.")
            
            try:
                # Get current state
                applied = {m['version'] for m in self._get_applied_migrations()}
                available = self._get_migration_files("up")
                
                # Find pending migrations
                pending = []
                for version, filepath in available:
                    if version not in applied:
                        if target and version > target:
                            break
                        pending.append((version, filepath))
                
                if not pending:
                    logger.info("No pending migrations to apply")
                    return
                
                logger.info(f"Found {len(pending)} pending migration(s)")
                
                # Apply migrations
                total_time = 0
                for version, filepath in pending:
                    # Extract migration name from version
                    parts = version.split("_", 2)
                    name = parts[2] if len(parts) > 2 else "unnamed"
                    
                    exec_time = self._apply_migration(conn, filepath, version, name, dry_run)
                    if exec_time:
                        total_time += exec_time
                
                if not dry_run:
                    conn.commit()
                    logger.info(f"✅ All migrations applied successfully (total: {total_time}ms)")
                else:
                    logger.info("[DRY RUN] No changes were made to the database")
                    
            except Exception as e:
                if not dry_run:
                    conn.rollback()
                    logger.error(f"❌ Migration failed, rolling back transaction: {e}")
                raise
            finally:
                self._release_lock(conn)
    
    def down(self, target: str, dry_run: bool = False):
        """Rollback migrations down to target version.
        
        Args:
            target: Target migration version ('zero' for complete rollback)
            dry_run: If True, show what would be done without rolling back
        """
        self._ensure_migrations_table()
        
        with self.get_connection(autocommit=False) as conn:
            # Acquire lock
            if not self._acquire_lock(conn):
                raise MigrationError("Could not acquire migration lock. Another migration may be in progress.")
            
            try:
                # Get current state
                applied = self._get_applied_migrations()
                if not applied:
                    logger.info("No migrations to rollback")
                    return
                
                # Find migrations to rollback
                to_rollback = []
                for migration in reversed(applied):
                    version = migration['version']
                    if target == "zero" or version > target:
                        # Find corresponding down file
                        down_file = self.migrations_dir / f"{version}_down.sql"
                        if down_file.exists():
                            name = migration.get('name', 'unnamed')
                            to_rollback.append((version, name, down_file))
                        else:
                            raise MigrationError(f"Down migration file not found: {down_file}")
                    else:
                        break
                
                if not to_rollback:
                    logger.info("No migrations to rollback")
                    return
                
                logger.info(f"Found {len(to_rollback)} migration(s) to rollback")
                
                # Rollback migrations
                total_time = 0
                for version, name, filepath in to_rollback:
                    exec_time = self._rollback_migration(conn, filepath, version, name, dry_run)
                    if exec_time:
                        total_time += exec_time
                
                if not dry_run:
                    conn.commit()
                    logger.info(f"✅ All rollbacks completed successfully (total: {total_time}ms)")
                else:
                    logger.info("[DRY RUN] No changes were made to the database")
                    
            except Exception as e:
                if not dry_run:
                    conn.rollback()
                    logger.error(f"❌ Rollback failed, rolling back transaction: {e}")
                raise
            finally:
                self._release_lock(conn)
    
    def status(self):
        """Show current migration status."""
        self._ensure_migrations_table()
        
        # Get applied migrations
        applied = self._get_applied_migrations()
        applied_versions = {m['version'] for m in applied}
        
        # Get available migrations
        available_up = self._get_migration_files("up")
        available_down = self._get_migration_files("down")
        down_versions = {v for v, _ in available_down}
        
        # Build status table
        table_data = []
        for version, _ in available_up:
            parts = version.split("_", 2)
            name = parts[2] if len(parts) > 2 else "unnamed"
            
            if version in applied_versions:
                migration = next(m for m in applied if m['version'] == version)
                status = "✓ Applied"
                applied_at = migration['applied_at'].strftime("%Y-%m-%d %H:%M:%S")
                exec_time = f"{migration['execution_time_ms']}ms" if migration['execution_time_ms'] else "N/A"
            else:
                status = "○ Pending"
                applied_at = "-"
                exec_time = "-"
            
            has_down = "✓" if version in down_versions else "✗"
            table_data.append([version, name, status, applied_at, exec_time, has_down])
        
        # Print status
        headers = ["Version", "Name", "Status", "Applied At", "Exec Time", "Reversible"]
        print("\nMigration Status:")
        print(self._format_table(table_data, headers))
        
        # Summary
        total_applied = len(applied_versions)
        total_pending = len(available_up) - total_applied
        print(f"\nSummary: {total_applied} applied, {total_pending} pending")
        
        if applied:
            latest = applied[-1]
            print(f"Latest: {latest['version']} (applied {latest['applied_at']})")
    
    def history(self, limit: int = 10):
        """Show migration history.
        
        Args:
            limit: Number of recent migrations to show
        """
        self._ensure_migrations_table()
        
        applied = self._get_applied_migrations()
        if not applied:
            print("No migration history")
            return
        
        # Show recent migrations
        recent = applied[-limit:] if limit else applied
        
        table_data = []
        for migration in reversed(recent):
            table_data.append([
                migration['version'],
                migration['name'],
                migration['applied_at'].strftime("%Y-%m-%d %H:%M:%S"),
                f"{migration['execution_time_ms']}ms" if migration['execution_time_ms'] else "N/A",
                migration['applied_by']
            ])
        
        headers = ["Version", "Name", "Applied At", "Exec Time", "Applied By"]
        print(f"\nMigration History (last {limit} entries):")
        print(self._format_table(table_data, headers))
    
    def pending(self):
        """List pending migrations."""
        self._ensure_migrations_table()
        
        # Get applied migrations
        applied = {m['version'] for m in self._get_applied_migrations()}
        
        # Get available migrations
        available = self._get_migration_files("up")
        
        # Find pending
        pending = []
        for version, filepath in available:
            if version not in applied:
                parts = version.split("_", 2)
                name = parts[2] if len(parts) > 2 else "unnamed"
                pending.append([version, name, filepath.name])
        
        if not pending:
            print("No pending migrations")
            return
        
        headers = ["Version", "Name", "File"]
        print(f"\nPending Migrations ({len(pending)} total):")
        print(self._format_table(pending, headers))
    
    def verify(self):
        """Verify migration checksums match current files."""
        self._ensure_migrations_table()
        
        applied = self._get_applied_migrations()
        if not applied:
            print("No migrations to verify")
            return
        
        mismatches = []
        missing = []
        
        for migration in applied:
            version = migration['version']
            filepath = self.migrations_dir / f"{version}_up.sql"
            
            if not filepath.exists():
                missing.append(version)
                continue
            
            with open(filepath) as f:
                content = f.read()
            
            current_checksum = self._calculate_checksum(content)
            if current_checksum != migration['checksum']:
                mismatches.append((version, migration['checksum'], current_checksum))
        
        if not mismatches and not missing:
            print("✅ All migration checksums verified successfully")
            return
        
        if missing:
            print("\n❌ Missing migration files:")
            for version in missing:
                print(f"  - {version}")
        
        if mismatches:
            print("\n❌ Checksum mismatches detected:")
            for version, expected, actual in mismatches:
                print(f"  - {version}")
                print(f"    Expected: {expected}")
                print(f"    Actual:   {actual}")
        
        print("\n⚠️  WARNING: Migration files have been modified after being applied!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration runner with transaction support"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # up command
    up_parser = subparsers.add_parser("up", help="Apply pending migrations")
    up_parser.add_argument(
        "--target",
        help="Target migration version (default: apply all)"
    )
    up_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without applying"
    )
    
    # down command
    down_parser = subparsers.add_parser("down", help="Rollback migrations")
    down_parser.add_argument(
        "--target",
        required=True,
        help="Target migration version (use 'zero' for complete rollback)"
    )
    down_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without rolling back"
    )
    
    # status command
    subparsers.add_parser("status", help="Show migration status")
    
    # history command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of entries to show (default: 10)"
    )
    
    # pending command
    subparsers.add_parser("pending", help="List pending migrations")
    
    # verify command
    subparsers.add_parser("verify", help="Verify migration checksums")
    
    # Global arguments
    parser.add_argument(
        "--database-url",
        help="Database URL (overrides configuration)"
    )
    parser.add_argument(
        "--migrations-dir",
        help="Directory containing migration files"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create runner
    migrations_dir = Path(args.migrations_dir) if args.migrations_dir else None
    runner = MigrationRunner(
        database_url=args.database_url,
        migrations_dir=migrations_dir
    )
    
    try:
        # Execute command
        if args.command == "up":
            runner.up(target=args.target, dry_run=args.dry_run)
        elif args.command == "down":
            runner.down(target=args.target, dry_run=args.dry_run)
        elif args.command == "status":
            runner.status()
        elif args.command == "history":
            runner.history(limit=args.limit)
        elif args.command == "pending":
            runner.pending()
        elif args.command == "verify":
            runner.verify()
        else:
            parser.print_help()
            sys.exit(1)
            
    except MigrationError as e:
        logger.error(f"Migration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()