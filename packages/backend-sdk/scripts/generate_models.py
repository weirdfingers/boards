#!/usr/bin/env python3
"""
Generate SQLAlchemy models from SQL DDL files.
Uses sqlacodegen-v2 to generate models from a temporary PostgreSQL database.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.boards.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_temp_database(base_url: str = None) -> tuple[str, str]:
    """Create a temporary PostgreSQL database for schema generation."""
    base_url = base_url or settings.database_url
    
    # Parse connection details
    if base_url.startswith("postgresql://"):
        conn_str = base_url.replace("postgresql://", "")
    else:
        raise ValueError("Only PostgreSQL is supported for model generation")
    
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
    temp_db_name = f"boards_temp_{uuid.uuid4().hex[:8]}"
    
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
                
                # Execute the entire DDL file as one statement
                # This handles functions and triggers properly
                conn.execute(text(ddl_content))
                conn.commit()

def generate_models_from_ddl(ddl_files: list[Path], output_file: Path):
    """Generate SQLAlchemy models from DDL files."""
    
    temp_url = None
    temp_db_name = None
    
    try:
        # Create temporary database
        logger.info("Creating temporary database...")
        temp_url, temp_db_name = create_temp_database()
        
        # Create engine for temp database
        engine = create_engine(temp_url)
        
        # Apply DDL files
        logger.info("Applying DDL files...")
        apply_ddl_files(engine, ddl_files)
        
        # Generate models using sqlacodegen
        logger.info("Generating SQLAlchemy models...")
        
        # Run sqlacodegen as subprocess
        cmd = [
            "sqlacodegen_v2",
            "--generator", "declarative",
            "--outfile", str(output_file),
            temp_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"sqlacodegen failed: {result.stderr}")
            raise RuntimeError(f"Model generation failed: {result.stderr}")
        
        logger.info(f"Models generated successfully: {output_file}")
        
        # Post-process the generated file
        post_process_models(output_file)
        
    finally:
        # Clean up temporary database
        if temp_url and temp_db_name:
            logger.info("Cleaning up temporary database...")
            drop_temp_database(temp_url, temp_db_name)

def post_process_models(output_file: Path):
    """Post-process generated models to add custom logic."""
    with open(output_file, 'r') as f:
        content = f.read()
    
    # Add custom imports
    custom_imports = """from typing import Optional, List
from datetime import datetime
from uuid import UUID

"""
    
    # Replace imports if needed
    if "from sqlalchemy import" in content:
        content = content.replace(
            "from sqlalchemy import",
            custom_imports + "from sqlalchemy import"
        )
    
    # Add __tablename__ to classes if missing (sqlacodegen should handle this)
    
    # Write back
    with open(output_file, 'w') as f:
        f.write(content)
    
    logger.info("Post-processing complete")

def main():
    """Main entry point."""
    # Paths
    project_root = Path(__file__).parent.parent
    ddl_dir = project_root / "migrations" / "schemas"
    output_file = project_root / "src" / "boards" / "database" / "models.py"
    
    # Ensure directories exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Get all DDL files in order
    ddl_files = sorted(ddl_dir.glob("*.sql"))
    
    if not ddl_files:
        logger.error(f"No DDL files found in {ddl_dir}")
        sys.exit(1)
    
    logger.info(f"Found {len(ddl_files)} DDL files:")
    for f in ddl_files:
        logger.info(f"  - {f.name}")
    
    # Generate models
    try:
        generate_models_from_ddl(ddl_files, output_file)
        print(f"\n✅ Models generated successfully: {output_file}")
    except Exception as e:
        logger.error(f"Failed to generate models: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()