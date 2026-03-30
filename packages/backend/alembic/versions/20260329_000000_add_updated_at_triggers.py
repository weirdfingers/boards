"""Add triggers to auto-update updated_at on all tables

Uses a custom PL/pgSQL trigger function rather than Supabase's moddatetime
extension so that migrations remain portable across any PostgreSQL host
(Docker Compose, AWS RDS, Cloud SQL, standalone, etc.). This coexists safely
with Supabase-hosted databases since all Boards objects live in the "boards"
schema, separate from Supabase's auth/storage schemas.

Revision ID: a1b2c3d4e5f6
Revises: b2fe3780f8c0
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b2fe3780f8c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schema name for all Boards tables
SCHEMA = "boards"

# All tables that have an updated_at column
TABLES_WITH_UPDATED_AT = [
    "tenants",
    "provider_configs",
    "users",
    "boards",
    "lora_models",
    "generations",
    "tags",
]


def upgrade() -> None:
    """Create a shared trigger function and attach it to all tables with updated_at."""
    # Create the shared trigger function
    op.execute(f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Attach trigger to each table
    for table in TABLES_WITH_UPDATED_AT:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
                BEFORE UPDATE ON {SCHEMA}.{table}
                FOR EACH ROW
                EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
        """)


def downgrade() -> None:
    """Remove all updated_at triggers and the shared function."""
    for table in TABLES_WITH_UPDATED_AT:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {SCHEMA}.{table};")

    op.execute(f"DROP FUNCTION IF EXISTS {SCHEMA}.update_updated_at_column();")
