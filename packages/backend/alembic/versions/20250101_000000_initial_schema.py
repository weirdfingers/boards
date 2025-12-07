"""
Initial schema with uuid-ossp extension and core tables.

Revision ID: 20250101_000000_initial_schema
Revises:
Create Date: 2025-01-01 00:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[reportMissingImports]

# revision identifiers, used by Alembic.
revision = "20250101_000000_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# Schema name for all Boards tables
SCHEMA = "boards"


def upgrade() -> None:
    # Create the boards schema
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA};")

    # Required extension for uuid_generate_v4 (in public schema, accessible everywhere)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # tenants
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="tenants_pkey"),
        sa.UniqueConstraint("slug", name="tenants_slug_key"),
        schema=SCHEMA,
    )

    # provider_configs
    op.create_table(
        "provider_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="provider_configs_pkey"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
            name="provider_configs_tenant_id_fkey",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "provider_name",
            name="provider_configs_tenant_id_provider_name_key",
        ),
        schema=SCHEMA,
    )

    # users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("auth_provider", sa.String(length=50), nullable=False),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255)),
        sa.Column("display_name", sa.String(length=255)),
        sa.Column("avatar_url", sa.Text()),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
            name="users_tenant_id_fkey",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "auth_provider",
            "auth_subject",
            name="users_tenant_id_auth_provider_auth_subject_key",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_users_auth",
        "users",
        ["auth_provider", "auth_subject"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index("idx_users_tenant", "users", ["tenant_id"], unique=False, schema=SCHEMA)

    # boards
    op.create_table(
        "boards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="boards_pkey"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            [f"{SCHEMA}.users.id"],
            ondelete="CASCADE",
            name="boards_owner_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
            name="boards_tenant_id_fkey",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_boards_owner", "boards", ["owner_id"], unique=False, schema=SCHEMA)
    op.create_index("idx_boards_tenant", "boards", ["tenant_id"], unique=False, schema=SCHEMA)

    # lora_models
    op.create_table(
        "lora_models",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_model", sa.String(length=100), nullable=False),
        sa.Column("storage_url", sa.Text(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trigger_word", sa.String(length=100)),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="lora_models_pkey"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
            name="lora_models_tenant_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            ondelete="CASCADE",
            name="lora_models_user_id_fkey",
        ),
        schema=SCHEMA,
    )

    # board_members
    op.create_table(
        "board_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("board_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=False)),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="board_members_pkey"),
        sa.UniqueConstraint(
            "board_id", "user_id", name="board_members_board_id_user_id_key"
        ),
        sa.CheckConstraint(
            "role::text = ANY (ARRAY['viewer'::character varying, "
            "'editor'::character varying, 'admin'::character varying]::text[])",
            name="board_members_role_check",
        ),
        sa.ForeignKeyConstraint(
            ["board_id"],
            [f"{SCHEMA}.boards.id"],
            ondelete="CASCADE",
            name="board_members_board_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            [f"{SCHEMA}.users.id"],
            name="board_members_invited_by_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            ondelete="CASCADE",
            name="board_members_user_id_fkey",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_board_members_board",
        "board_members",
        ["board_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "idx_board_members_user",
        "board_members",
        ["user_id"],
        unique=False,
        schema=SCHEMA,
    )

    # generations
    op.create_table(
        "generations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("board_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("generator_name", sa.String(length=100), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column(
            "input_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'pending'::character varying"),
        ),
        sa.Column("storage_url", sa.Text()),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column(
            "additional_files",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "output_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("parent_generation_id", postgresql.UUID(as_uuid=False)),
        sa.Column(
            "input_generation_ids",
            postgresql.ARRAY(postgresql.UUID()),
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("external_job_id", sa.String(length=255)),
        sa.Column("progress", sa.Numeric(5, 2), server_default=sa.text("0.0")),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="generations_pkey"),
        sa.ForeignKeyConstraint(
            ["board_id"],
            [f"{SCHEMA}.boards.id"],
            ondelete="CASCADE",
            name="generations_board_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["parent_generation_id"],
            [f"{SCHEMA}.generations.id"],
            name="generations_parent_generation_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
            name="generations_tenant_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            ondelete="CASCADE",
            name="generations_user_id_fkey",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_generations_board", "generations", ["board_id"], unique=False, schema=SCHEMA
    )
    op.create_index(
        "idx_generations_lineage",
        "generations",
        ["parent_generation_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "idx_generations_status", "generations", ["status"], unique=False, schema=SCHEMA
    )
    op.create_index(
        "idx_generations_tenant", "generations", ["tenant_id"], unique=False, schema=SCHEMA
    )
    op.create_index(
        "idx_generations_user", "generations", ["user_id"], unique=False, schema=SCHEMA
    )

    # credit_transactions
    op.create_table(
        "credit_transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(10, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(10, 4), nullable=False),
        sa.Column("generation_id", postgresql.UUID(as_uuid=False)),
        sa.Column("description", sa.Text()),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="credit_transactions_pkey"),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            [f"{SCHEMA}.generations.id"],
            name="credit_transactions_generation_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
            name="credit_transactions_tenant_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            ondelete="CASCADE",
            name="credit_transactions_user_id_fkey",
        ),
        sa.CheckConstraint(
            "transaction_type::text = ANY (ARRAY["
            "'reserve'::character varying, 'finalize'::character varying, "
            "'refund'::character varying, 'purchase'::character varying, "
            "'grant'::character varying]::text[])",
            name="credit_transactions_transaction_type_check",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_credit_transactions_user",
        "credit_transactions",
        ["user_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    # drop in reverse dependency order
    op.drop_index(
        "idx_credit_transactions_user", table_name="credit_transactions", schema=SCHEMA
    )
    op.drop_table("credit_transactions", schema=SCHEMA)

    op.drop_index("idx_generations_user", table_name="generations", schema=SCHEMA)
    op.drop_index("idx_generations_tenant", table_name="generations", schema=SCHEMA)
    op.drop_index("idx_generations_status", table_name="generations", schema=SCHEMA)
    op.drop_index("idx_generations_lineage", table_name="generations", schema=SCHEMA)
    op.drop_index("idx_generations_board", table_name="generations", schema=SCHEMA)
    op.drop_table("generations", schema=SCHEMA)

    op.drop_index("idx_board_members_user", table_name="board_members", schema=SCHEMA)
    op.drop_index("idx_board_members_board", table_name="board_members", schema=SCHEMA)
    op.drop_table("board_members", schema=SCHEMA)

    op.drop_table("lora_models", schema=SCHEMA)

    op.drop_index("idx_boards_tenant", table_name="boards", schema=SCHEMA)
    op.drop_index("idx_boards_owner", table_name="boards", schema=SCHEMA)
    op.drop_table("boards", schema=SCHEMA)

    op.drop_index("idx_users_tenant", table_name="users", schema=SCHEMA)
    op.drop_index("idx_users_auth", table_name="users", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)

    op.drop_table("provider_configs", schema=SCHEMA)

    op.drop_table("tenants", schema=SCHEMA)

    # Drop the schema with CASCADE to remove alembic_version table too
    # Will fail if non-Boards objects exist (beyond alembic_version), which is intentional
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE;")
