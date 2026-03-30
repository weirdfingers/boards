"""Add plugin_results JSONB column to generations table.

Stores execution results from artifact plugins (e.g. C2PA signing,
watermarking, content analysis) that run between generation and upload.

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "boards"


def upgrade() -> None:
    op.add_column(
        "generations",
        sa.Column("plugin_results", postgresql.JSONB(), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("generations", "plugin_results", schema=SCHEMA)
