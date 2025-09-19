---
sidebar_position: 2
---

# Database Migrations

Boards uses **Alembic** with async engines and timestamped filenames. ORM models in `boards.dbmodels` are the source of truth.

## Migration Philosophy

We avoid schema drift by:

1. Maintaining authoritative SQLAlchemy models in code (`boards.dbmodels`)
2. Autogenerating Alembic revisions from model diffs
3. Writing explicit revision scripts for non-ORM objects (extensions, functions, triggers, RLS)
4. Requiring reversible `downgrade()` where feasible; document exceptions

## Quick Workflow

```bash
# 1) Make model changes in src/boards/dbmodels/
# 2) Autogenerate a new revision
uv run alembic revision -m "add user preferences" --autogenerate

# 3) Review and edit the generated revision file under alembic/versions/
# 4) Apply the migration
uv run alembic upgrade head

# 5) Rollback if needed
uv run alembic downgrade -1
```

## Timestamped Filenames

Alembic is configured to generate filenames like:

```
20250901_120301_add_user_preferences.py
```

This improves readability and sort order in version control.

## Initial Setup

On a new environment:

```bash
cd packages/backend
uv run alembic upgrade head
```

This creates all tables and enables required extensions (e.g., `uuid-ossp`).

## Managing Non-ORM Objects

Use explicit SQL in revisions for extensions, triggers, functions, and policies.

Example (RLS policy):

```python
from alembic import op

def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'users' AND policyname = 'users_isolation'
            ) THEN
                CREATE POLICY users_isolation ON users
                    USING (tenant_id = current_setting('app.tenant_id')::uuid);
            END IF;
        END$$;
        """
    )

def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'users' AND policyname = 'users_isolation'
            ) THEN
                DROP POLICY users_isolation ON users;
            END IF;
        END$$;
        """
    )
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
```

Counter-example (avoid):

```python
# Missing guards, non-reversible
op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
op.execute("CREATE POLICY users_isolation ON users USING (...);")

def downgrade():
    pass
```

## Data Migrations

Write data backfills inside revisions. Prefer reversible operations when feasible; otherwise, document irreversibility.

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

users = table('users', column('id', sa.String), column('display_name', sa.String))

def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(users.update().where(users.c.display_name == None).values(display_name=''))

def downgrade() -> None:
    # Best-effort reversal if needed
    pass
```

## Autogenerate Tips

- Keep `naming_convention` in `dbmodels` to produce stable diffs
- Use `compare_type=True` (enabled) to detect type changes
- Review generated diffs carefully—add indexes/constraints where required

## Common Commands

```bash
# New revision (blank)
uv run alembic revision -m "empty revision"

# New revision from model changes
uv run alembic revision -m "add columns" --autogenerate

# Upgrade / downgrade
uv run alembic upgrade head
uv run alembic downgrade base

# Show history
uv run alembic history --verbose
```

## CI Enforcement

Recommended checks:

- `uv run alembic upgrade head && uv run alembic downgrade base`
- Lint new revisions to ensure `downgrade()` is present and non-empty

## File Structure

```
packages/backend/
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
└── src/boards/dbmodels/
```

The `boards.database.models` module re-exports from `boards.dbmodels` for compatibility, but new imports should use `boards.dbmodels` directly.
