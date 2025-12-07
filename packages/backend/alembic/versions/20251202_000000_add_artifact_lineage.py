"""add artifact lineage with input_artifacts

Revision ID: add_artifact_lineage
Revises: cdad231052d5
Create Date: 2025-12-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_artifact_lineage"
down_revision: Union[str, Sequence[str], None] = "cdad231052d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schema name for all Boards tables
SCHEMA = "boards"


def upgrade() -> None:
    """Upgrade schema to use input_artifacts for lineage tracking."""
    # Add input_artifacts JSONB column
    op.add_column(
        "generations",
        sa.Column(
            "input_artifacts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        schema=SCHEMA,
    )

    # Migrate existing data from input_generation_ids to input_artifacts
    # For backwards compatibility, use role="input" for legacy data
    op.execute(f"""
        UPDATE {SCHEMA}.generations
        SET input_artifacts = (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'generation_id', gen_id::text,
                    'role', 'input',
                    'artifact_type', COALESCE(g.artifact_type, 'unknown')
                )
            ), '[]'::jsonb)
            FROM unnest(input_generation_ids) AS gen_id
            LEFT JOIN {SCHEMA}.generations g ON g.id = gen_id
        )
        WHERE input_generation_ids IS NOT NULL
        AND array_length(input_generation_ids, 1) > 0
    """)

    # Add GIN index for JSONB queries
    op.create_index(
        "idx_generations_input_artifacts_gin",
        "generations",
        ["input_artifacts"],
        unique=False,
        postgresql_using="gin",
        schema=SCHEMA,
    )

    # Drop old lineage index
    op.drop_index("idx_generations_lineage", table_name="generations", schema=SCHEMA)

    # Drop old foreign key constraint on parent_generation_id
    op.drop_constraint(
        "generations_parent_generation_id_fkey",
        "generations",
        type_="foreignkey",
        schema=SCHEMA,
    )

    # Drop old columns
    op.drop_column("generations", "parent_generation_id", schema=SCHEMA)
    op.drop_column("generations", "input_generation_ids", schema=SCHEMA)


def downgrade() -> None:
    """Downgrade schema back to parent_generation_id and input_generation_ids."""
    # Add back old columns
    op.add_column(
        "generations",
        sa.Column(
            "input_generation_ids",
            postgresql.ARRAY(postgresql.UUID()),
            server_default=sa.text("'{}'::uuid[]"),
            autoincrement=False,
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "generations",
        sa.Column("parent_generation_id", postgresql.UUID(), autoincrement=False, nullable=True),
        schema=SCHEMA,
    )

    # Migrate data back from input_artifacts to input_generation_ids
    op.execute(f"""
        UPDATE {SCHEMA}.generations
        SET input_generation_ids = (
            SELECT COALESCE(
                array_agg((elem->>'generation_id')::uuid),
                '{{}}'::uuid[]
            )
            FROM jsonb_array_elements(input_artifacts) elem
        )
        WHERE input_artifacts IS NOT NULL
        AND jsonb_array_length(input_artifacts) > 0
    """)

    # Recreate foreign key constraint
    op.create_foreign_key(
        "generations_parent_generation_id_fkey",
        "generations",
        "generations",
        ["parent_generation_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )

    # Recreate old index
    op.create_index("idx_generations_lineage", "generations", ["parent_generation_id"], unique=False, schema=SCHEMA)

    # Drop new index and column
    op.drop_index("idx_generations_input_artifacts_gin", table_name="generations", schema=SCHEMA)
    op.drop_column("generations", "input_artifacts", schema=SCHEMA)
