#!/usr/bin/env python3
"""
Generate migration scripts by comparing current database to target schema.
Uses migra to create UP/DOWN migration scripts.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
import logging
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.boards.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_temp_database(base_url: str = None) -> tuple[str, str]:
    """Create a temporary PostgreSQL database."""
    base_url = base_url or settings.database_url
    
    # Parse connection details
    if base_url.startswith("postgresql://"):
        conn_str = base_url.replace("postgresql://", "")
    else:
        raise ValueError("Only PostgreSQL is supported for migrations")
    
    # Extract components
    if "@" in conn_str:
        auth, host_db = conn_str.split("@")
        if "/" in host_db:
            host, db = host_db.split("/", 1)
        else:
            host, db = host_db, "postgres"
    else:
        raise ValueError("Invalid database URL format")
    
    if ":" in auth:
        user, password = auth.split(":")
    else:
        user, password = auth, ""
    
    # Create temporary database name
    import uuid
    temp_db_name = f"boards_migration_{uuid.uuid4().hex[:8]}"
    
    # Connect to PostgreSQL to create temp database
    conn = psycopg2.connect(
        host=host.split(":")[0],
        port=int(host.split(":")[1]) if ":" in host else 5432,
        user=user,
        password=password,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE {temp_db_name}")
    cursor.close()
    conn.close()
    
    # Return temp database URL
    temp_url = f"postgresql://{user}:{password}@{host}/{temp_db_name}"
    return temp_url, temp_db_name

def drop_temp_database(base_url: str, db_name: str):
    """Drop the temporary database."""
    # Parse connection details
    conn_str = base_url.replace("postgresql://", "")
    auth, host_db = conn_str.split("@")
    host = host_db.split("/")[0]
    user, password = auth.split(":") if ":" in auth else (auth, "")
    
    # Connect and drop database
    conn = psycopg2.connect(
        host=host.split(":")[0],
        port=int(host.split(":")[1]) if ":" in host else 5432,
        user=user,
        password=password,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
    cursor.close()
    conn.close()

def apply_ddl_files(engine, ddl_files: list[Path]):
    """Apply DDL files to the database."""
    with engine.connect() as conn:
        for ddl_file in ddl_files:
            logger.info(f"Applying DDL: {ddl_file}")
            with open(ddl_file) as f:
                ddl_content = f.read()
                conn.execute(text(ddl_content))
                conn.commit()

def generate_migration(
    current_db_url: str,
    target_ddl_files: list[Path],
    migration_name: str,
    output_dir: Path
) -> tuple[Path, Path]:
    """Generate migration scripts from current state to target schema."""
    
    temp_url = None
    temp_db_name = None
    
    try:
        # Create temporary database with target schema
        logger.info("Creating temporary database with target schema...")
        temp_url, temp_db_name = create_temp_database()
        
        # Apply target DDL to temp database
        engine = create_engine(temp_url)
        apply_ddl_files(engine, target_ddl_files)
        
        logger.info("Generating migration using migra...")
        
        # Generate forward migration (UP)
        result = subprocess.run(
            ["migra", "--unsafe", current_db_url, temp_url],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning(f"Migra returned non-zero: {result.stderr}")
        
        up_sql = result.stdout
        
        # Generate reverse migration (DOWN)
        result = subprocess.run(
            ["migra", "--unsafe", temp_url, current_db_url],
            capture_output=True,
            text=True
        )
        
        down_sql = result.stdout
        
        # Create migration files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_id = f"{timestamp}_{migration_name}"
        
        up_file = output_dir / f"{migration_id}_up.sql"
        down_file = output_dir / f"{migration_id}_down.sql"
        
        # Write migration files
        with open(up_file, 'w') as f:
            f.write(f"-- Migration: {migration_id} UP\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
            if up_sql.strip():
                f.write(up_sql)
            else:
                f.write("-- No changes detected\n")
        
        with open(down_file, 'w') as f:
            f.write(f"-- Migration: {migration_id} DOWN\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
            if down_sql.strip():
                f.write(down_sql)
            else:
                f.write("-- No changes detected\n")
        
        return up_file, down_file
        
    finally:
        # Clean up temporary database
        if temp_url and temp_db_name:
            logger.info("Cleaning up temporary database...")
            drop_temp_database(temp_url, temp_db_name)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate migration scripts')
    parser.add_argument(
        '--name',
        required=True,
        help='Migration name (e.g., add_user_preferences)'
    )
    parser.add_argument(
        '--current-db',
        default=settings.database_url,
        help='Current database URL (defaults to configured database)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without creating files'
    )
    
    args = parser.parse_args()
    
    # Paths
    project_root = Path(__file__).parent.parent
    ddl_dir = project_root / "migrations" / "schemas"
    output_dir = project_root / "migrations" / "generated"
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all DDL files in order
    ddl_files = sorted(ddl_dir.glob("*.sql"))
    
    if not ddl_files:
        logger.error(f"No DDL files found in {ddl_dir}")
        sys.exit(1)
    
    logger.info(f"Found {len(ddl_files)} DDL files")
    
    try:
        if args.dry_run:
            logger.info("DRY RUN: Would generate migration files")
            logger.info(f"  Name: {args.name}")
            logger.info(f"  Current DB: {args.current_db}")
            logger.info(f"  Target DDL: {', '.join(f.name for f in ddl_files)}")
        else:
            up_file, down_file = generate_migration(
                current_db_url=args.current_db,
                target_ddl_files=ddl_files,
                migration_name=args.name,
                output_dir=output_dir
            )
            
            print(f"\n✅ Migration generated successfully:")
            print(f"  UP:   {up_file}")
            print(f"  DOWN: {down_file}")
            
            # Check if migration has changes
            with open(up_file) as f:
                if "No changes detected" in f.read():
                    print("\n⚠️  No schema changes detected")
                    
    except Exception as e:
        logger.error(f"Failed to generate migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()