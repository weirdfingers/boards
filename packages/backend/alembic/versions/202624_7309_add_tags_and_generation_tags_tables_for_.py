"""Add tags and generation_tags tables for wardrobe categorization

Revision ID: b2fe3780f8c0
Revises: add_artifact_lineage
Create Date: 2026-02-04 07:30:09.146288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2fe3780f8c0'
down_revision: Union[str, Sequence[str], None] = 'add_artifact_lineage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schema name for all Boards tables
SCHEMA = "boards"


def upgrade() -> None:
    """Add tags and generation_tags tables for wardrobe categorization."""
    # Create tags table for categorizing wardrobe items (model, top, bottom, shoes, etc.)
    op.create_table('tags',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['boards.tenants.id'], name='tags_tenant_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='tags_pkey'),
        sa.UniqueConstraint('tenant_id', 'slug', name='tags_tenant_id_slug_key'),
        schema=SCHEMA
    )
    op.create_index('idx_tags_slug', 'tags', ['slug'], unique=False, schema=SCHEMA)
    op.create_index('idx_tags_tenant', 'tags', ['tenant_id'], unique=False, schema=SCHEMA)

    # Create generation_tags association table for many-to-many relationship
    op.create_table('generation_tags',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('generation_id', sa.Uuid(), nullable=False),
        sa.Column('tag_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['generation_id'], ['boards.generations.id'], name='generation_tags_generation_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['boards.tags.id'], name='generation_tags_tag_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='generation_tags_pkey'),
        sa.UniqueConstraint('generation_id', 'tag_id', name='generation_tags_generation_id_tag_id_key'),
        schema=SCHEMA
    )
    op.create_index('idx_generation_tags_generation', 'generation_tags', ['generation_id'], unique=False, schema=SCHEMA)
    op.create_index('idx_generation_tags_tag', 'generation_tags', ['tag_id'], unique=False, schema=SCHEMA)


def downgrade() -> None:
    """Remove tags and generation_tags tables."""
    # Drop generation_tags table and its indexes
    op.drop_index('idx_generation_tags_tag', table_name='generation_tags', schema=SCHEMA)
    op.drop_index('idx_generation_tags_generation', table_name='generation_tags', schema=SCHEMA)
    op.drop_table('generation_tags', schema=SCHEMA)

    # Drop tags table and its indexes
    op.drop_index('idx_tags_tenant', table_name='tags', schema=SCHEMA)
    op.drop_index('idx_tags_slug', table_name='tags', schema=SCHEMA)
    op.drop_table('tags', schema=SCHEMA)
