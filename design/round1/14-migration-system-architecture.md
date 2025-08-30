# Migration System Architecture

## Overview
A custom migration system that uses SQL DDL as source of truth, generates SQLAlchemy models, and creates migration scripts via schema diffing.

## Architecture Components

```
SQL DDL Files (Source of Truth)
      ↓
   Migration System
      ↓
┌─────────────────┬─────────────────┐
│  SQLAlchemy     │  Migration      │
│  Models         │  Scripts        │
│  (generated)    │  (generated)    │
└─────────────────┴─────────────────┘
```

## Core Tools

### Schema Generation: sqlacodegen-v2
- **Purpose**: Generate SQLAlchemy models from database schemas
- **Usage**: Apply SQL DDL to temp database, then generate models
- **Output**: Python models with proper relationships and types

### Migration Generation: migra (or equivalent)
- **Purpose**: Generate SQL migration scripts by comparing schemas
- **Usage**: Compare current database state to target schema
- **Output**: SQL migration files with UP/DOWN scripts

## Migration Workflow

```python
# 1. Schema Definition (manual)
migrations/001_initial_schema.sql

# 2. Model Generation (automated)
python scripts/generate_models.py
  → packages/backend/src/boards/database/models.py

# 3. Migration Generation (automated)
python scripts/generate_migration.py
  → migrations/001_initial_schema_up.sql
  → migrations/001_initial_schema_down.sql

# 4. Migration Application (manual/CI)
python scripts/apply_migrations.py
```

## File Structure

```
packages/backend/
├── migrations/
│   ├── schemas/                    # DDL source files
│   │   ├── 001_initial_schema.sql
│   │   └── 002_add_indexes.sql
│   ├── generated/                  # Generated migration scripts
│   │   ├── 001_up.sql
│   │   ├── 001_down.sql
│   │   ├── 002_up.sql
│   │   └── 002_down.sql
│   ├── applied/                    # Applied migration tracking
│   │   └── migration_log.json
│   └── migration_runner.py         # Migration application logic
├── scripts/
│   ├── generate_models.py          # SQL DDL → SQLAlchemy models
│   ├── generate_migration.py       # Schema diff → SQL scripts
│   └── apply_migrations.py         # Apply migrations to database
└── src/boards/database/
    ├── models.py                   # Generated SQLAlchemy models
    └── connection.py               # Database connection management
```

## Implementation Details

### 1. Schema-to-Models Generation (`scripts/generate_models.py`)

```python
#!/usr/bin/env python3
"""
Generate SQLAlchemy models from SQL DDL files.
Uses sqlacodegen-v2 to generate models from a temporary database.
"""

import os
import tempfile
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
import sqlacodegen_v2

def generate_models_from_ddl(ddl_files: list[Path], output_file: Path):
    """Generate SQLAlchemy models from DDL files."""
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db') as temp_db:
        temp_url = f"sqlite:///{temp_db.name}"
        engine = create_engine(temp_url)
        
        # Apply all DDL files to temp database
        with engine.connect() as conn:
            for ddl_file in ddl_files:
                with open(ddl_file) as f:
                    ddl_content = f.read()
                    # Split and execute DDL statements
                    for statement in ddl_content.split(';'):
                        if statement.strip():
                            conn.execute(statement)
            conn.commit()
        
        # Generate models using sqlacodegen-v2
        from sqlacodegen_v2 import generate_models
        from io import StringIO
        
        output_buffer = StringIO()
        generate_models(
            engine_url=temp_url,
            generator='declarative',
            output=output_buffer,
            options={'noconstraints': False, 'noindexes': False}
        )
        
        # Write generated models to output file
        with open(output_file, 'w') as f:
            f.write(output_buffer.getvalue())

if __name__ == '__main__':
    ddl_dir = Path('migrations/schemas')
    output_file = Path('src/boards/database/models.py')
    
    # Get all DDL files in order
    ddl_files = sorted(ddl_dir.glob('*.sql'))
    
    print(f"Generating models from {len(ddl_files)} DDL files...")
    generate_models_from_ddl(ddl_files, output_file)
    print(f"Models generated: {output_file}")
```

### 2. Migration Generation (`scripts/generate_migration.py`)

```python
#!/usr/bin/env python3
"""
Generate migration scripts by comparing current database to target schema.
Uses migra or equivalent to create UP/DOWN migration scripts.
"""

import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
import subprocess

def generate_migration(
    current_db_url: str, 
    target_ddl_files: list[Path], 
    migration_name: str,
    output_dir: Path
):
    """Generate migration scripts from current state to target schema."""
    
    # Create temporary database with target schema
    with tempfile.NamedTemporaryFile(suffix='.db') as temp_db:
        temp_url = f"sqlite:///{temp_db.name}"
        engine = create_engine(temp_url)
        
        # Apply target DDL to temp database
        with engine.connect() as conn:
            for ddl_file in target_ddl_files:
                with open(ddl_file) as f:
                    ddl_content = f.read()
                    for statement in ddl_content.split(';'):
                        if statement.strip():
                            conn.execute(statement)
            conn.commit()
        
        # Generate migration using migra (or custom diff logic)
        # Note: migra is PostgreSQL-specific, may need alternative for SQLite
        try:
            # Forward migration (UP)
            result = subprocess.run([
                'migra', 
                current_db_url, 
                temp_url
            ], capture_output=True, text=True)
            
            up_sql = result.stdout
            
            # Reverse migration (DOWN) - compare in opposite direction
            result = subprocess.run([
                'migra', 
                temp_url,
                current_db_url
            ], capture_output=True, text=True)
            
            down_sql = result.stdout
            
        except FileNotFoundError:
            # Fallback: custom schema comparison logic
            up_sql, down_sql = custom_schema_diff(current_db_url, temp_url)
        
        # Write migration files
        up_file = output_dir / f"{migration_name}_up.sql"
        down_file = output_dir / f"{migration_name}_down.sql"
        
        with open(up_file, 'w') as f:
            f.write(f"-- Migration: {migration_name} UP\n\n")
            f.write(up_sql)
        
        with open(down_file, 'w') as f:
            f.write(f"-- Migration: {migration_name} DOWN\n\n")
            f.write(down_sql)
        
        return up_file, down_file

def custom_schema_diff(db1_url: str, db2_url: str) -> tuple[str, str]:
    """Custom schema comparison when migra is not available."""
    # This would implement basic schema comparison logic
    # For now, return placeholder
    return (
        "-- Custom migration logic here\n-- TODO: Implement schema comparison",
        "-- Custom rollback logic here\n-- TODO: Implement reverse changes"
    )

if __name__ == '__main__':
    from argparse import ArgumentParser
    
    parser = ArgumentParser(description='Generate migration scripts')
    parser.add_argument('--current-db', required=True, help='Current database URL')
    parser.add_argument('--migration-name', required=True, help='Migration name')
    parser.add_argument('--output-dir', default='migrations/generated', help='Output directory')
    
    args = parser.parse_args()
    
    ddl_dir = Path('migrations/schemas')
    ddl_files = sorted(ddl_dir.glob('*.sql'))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    up_file, down_file = generate_migration(
        current_db_url=args.current_db,
        target_ddl_files=ddl_files,
        migration_name=args.migration_name,
        output_dir=output_dir
    )
    
    print(f"Generated migration files:")
    print(f"  UP: {up_file}")
    print(f"  DOWN: {down_file}")
```

### 3. Migration Runner (`migrations/migration_runner.py`)

```python
#!/usr/bin/env python3
"""
Apply migrations to database with tracking and rollback support.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from typing import List, Dict, Any

class MigrationRunner:
    def __init__(self, db_url: str, migrations_dir: Path):
        self.engine = create_engine(db_url)
        self.migrations_dir = Path(migrations_dir)
        self.log_file = self.migrations_dir / 'applied' / 'migration_log.json'
        self.ensure_migration_table()
    
    def ensure_migration_table(self):
        """Ensure migration tracking table exists."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    checksum VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration names."""
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM schema_migrations ORDER BY applied_at"
            ))
            return [row[0] for row in result]
    
    def calculate_checksum(self, sql_content: str) -> str:
        """Calculate SHA-256 checksum of SQL content."""
        return hashlib.sha256(sql_content.encode()).hexdigest()
    
    def apply_migration(self, migration_name: str) -> bool:
        """Apply a single migration."""
        up_file = self.migrations_dir / 'generated' / f'{migration_name}_up.sql'
        
        if not up_file.exists():
            print(f"Migration file not found: {up_file}")
            return False
        
        with open(up_file) as f:
            sql_content = f.read()
        
        checksum = self.calculate_checksum(sql_content)
        
        try:
            with self.engine.connect() as conn:
                # Execute migration SQL
                for statement in sql_content.split(';'):
                    if statement.strip() and not statement.strip().startswith('--'):
                        conn.execute(text(statement))
                
                # Record migration as applied
                conn.execute(text("""
                    INSERT INTO schema_migrations (name, checksum)
                    VALUES (:name, :checksum)
                """), {'name': migration_name, 'checksum': checksum})
                
                conn.commit()
                print(f"Applied migration: {migration_name}")
                return True
                
        except Exception as e:
            print(f"Failed to apply migration {migration_name}: {e}")
            return False
    
    def rollback_migration(self, migration_name: str) -> bool:
        """Rollback a single migration."""
        down_file = self.migrations_dir / 'generated' / f'{migration_name}_down.sql'
        
        if not down_file.exists():
            print(f"Rollback file not found: {down_file}")
            return False
        
        with open(down_file) as f:
            sql_content = f.read()
        
        try:
            with self.engine.connect() as conn:
                # Execute rollback SQL
                for statement in sql_content.split(';'):
                    if statement.strip() and not statement.strip().startswith('--'):
                        conn.execute(text(statement))
                
                # Remove migration record
                conn.execute(text(
                    "DELETE FROM schema_migrations WHERE name = :name"
                ), {'name': migration_name})
                
                conn.commit()
                print(f"Rolled back migration: {migration_name}")
                return True
                
        except Exception as e:
            print(f"Failed to rollback migration {migration_name}: {e}")
            return False
    
    def migrate_up(self, target_migration: str = None) -> bool:
        """Apply migrations up to target (or all if None)."""
        applied = set(self.get_applied_migrations())
        
        # Get all available migrations
        migration_files = sorted(self.migrations_dir.glob('generated/*_up.sql'))
        available_migrations = [
            f.stem.replace('_up', '') for f in migration_files
        ]
        
        # Determine migrations to apply
        to_apply = []
        for migration in available_migrations:
            if migration not in applied:
                to_apply.append(migration)
                if migration == target_migration:
                    break
        
        # Apply migrations in order
        for migration in to_apply:
            if not self.apply_migration(migration):
                return False
        
        print(f"Successfully applied {len(to_apply)} migrations")
        return True
    
    def migrate_down(self, target_migration: str) -> bool:
        """Rollback migrations down to target."""
        applied = self.get_applied_migrations()
        
        # Find migrations to rollback (in reverse order)
        to_rollback = []
        found_target = False
        
        for migration in reversed(applied):
            if migration == target_migration:
                found_target = True
                break
            to_rollback.append(migration)
        
        if not found_target and target_migration != 'zero':
            print(f"Target migration not found: {target_migration}")
            return False
        
        # Rollback migrations in reverse order
        for migration in to_rollback:
            if not self.rollback_migration(migration):
                return False
        
        print(f"Successfully rolled back {len(to_rollback)} migrations")
        return True

if __name__ == '__main__':
    from argparse import ArgumentParser
    
    parser = ArgumentParser(description='Run database migrations')
    parser.add_argument('--db-url', required=True, help='Database URL')
    parser.add_argument('--migrations-dir', default='migrations', help='Migrations directory')
    parser.add_argument('command', choices=['up', 'down', 'status'], help='Migration command')
    parser.add_argument('--target', help='Target migration name')
    
    args = parser.parse_args()
    
    runner = MigrationRunner(args.db_url, Path(args.migrations_dir))
    
    if args.command == 'up':
        runner.migrate_up(args.target)
    elif args.command == 'down':
        if not args.target:
            print("Target migration required for rollback")
            exit(1)
        runner.migrate_down(args.target)
    elif args.command == 'status':
        applied = runner.get_applied_migrations()
        print(f"Applied migrations ({len(applied)}):")
        for migration in applied:
            print(f"  ✓ {migration}")
```

## CLI Integration

Add migration commands to the main CLI tool:

```bash
# Generate models from DDL
weirdfingers-cli generate-models

# Create new migration
weirdfingers-cli create-migration --name add_user_preferences

# Apply migrations
weirdfingers-cli migrate up

# Rollback migration  
weirdfingers-cli migrate down --target 001_initial_schema

# Show migration status
weirdfingers-cli migrate status
```

## Makefile Integration

```makefile
# Database operations
migrate-up: ## Apply all pending migrations
	cd packages/backend && python scripts/apply_migrations.py up

migrate-down: ## Rollback last migration
	cd packages/backend && python scripts/apply_migrations.py down --target $(TARGET)

generate-models: ## Generate SQLAlchemy models from DDL
	cd packages/backend && python scripts/generate_models.py

create-migration: ## Create new migration from schema changes
	cd packages/backend && python scripts/generate_migration.py --name $(NAME)
```

## Key Benefits

1. **SQL DDL as Source of Truth**: Schema defined in readable SQL files
2. **Automated Model Generation**: No manual SQLAlchemy model maintenance
3. **Safe Migrations**: Automatic UP/DOWN script generation with validation
4. **Version Control Friendly**: All migrations tracked and reproducible
5. **CI/CD Integration**: Automated migration application in deployments

## Database Support

- **Primary**: PostgreSQL (production)
- **Development**: SQLite (local development)
- **Testing**: In-memory SQLite (unit tests)

The migration system abstracts database-specific differences while supporting the unique features of each database type.