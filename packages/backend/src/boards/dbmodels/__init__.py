"""
Database models for Boards (authoritative ORM definitions).

This module defines the SQLAlchemy Base with a naming convention for stable
Alembic autogenerate diffs, and exposes `target_metadata` for Alembic.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Naming convention for deterministic constraint/index names in Alembic diffs
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all database models with type checking support."""

    metadata = MetaData(naming_convention=naming_convention)


class Tenants(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="tenants_pkey"),
        UniqueConstraint("slug", name="tenants_slug_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    provider_configs: Mapped[list["ProviderConfigs"]] = relationship(
        "ProviderConfigs", uselist=True, back_populates="tenant"
    )
    users: Mapped[list["Users"]] = relationship("Users", uselist=True, back_populates="tenant")
    boards: Mapped[list["Boards"]] = relationship("Boards", uselist=True, back_populates="tenant")
    lora_models: Mapped[list["LoraModels"]] = relationship(
        "LoraModels", uselist=True, back_populates="tenant"
    )
    generations: Mapped[list["Generations"]] = relationship(
        "Generations", uselist=True, back_populates="tenant"
    )
    credit_transactions: Mapped[list["CreditTransactions"]] = relationship(
        "CreditTransactions", uselist=True, back_populates="tenant"
    )


class ProviderConfigs(Base):
    __tablename__ = "provider_configs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="provider_configs_tenant_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="provider_configs_pkey"),
        UniqueConstraint(
            "tenant_id",
            "provider_name",
            name="provider_configs_tenant_id_provider_name_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    tenant: Mapped["Tenants"] = relationship("Tenants", back_populates="provider_configs")


class Users(Base):
    __tablename__ = "users"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="users_tenant_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="users_pkey"),
        UniqueConstraint(
            "tenant_id",
            "auth_provider",
            "auth_subject",
            name="users_tenant_id_auth_provider_auth_subject_key",
        ),
        Index("idx_users_auth", "auth_provider", "auth_subject"),
        Index("idx_users_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    tenant: Mapped["Tenants"] = relationship("Tenants", back_populates="users")
    boards: Mapped[list["Boards"]] = relationship("Boards", uselist=True, back_populates="owner")
    lora_models: Mapped[list["LoraModels"]] = relationship(
        "LoraModels", uselist=True, back_populates="user"
    )
    board_members: Mapped[list["BoardMembers"]] = relationship(
        "BoardMembers",
        uselist=True,
        foreign_keys="[BoardMembers.invited_by]",
        back_populates="users",
    )
    board_members_: Mapped[list["BoardMembers"]] = relationship(
        "BoardMembers",
        uselist=True,
        foreign_keys="[BoardMembers.user_id]",
        back_populates="user",
    )
    generations: Mapped[list["Generations"]] = relationship(
        "Generations", uselist=True, back_populates="user"
    )
    credit_transactions: Mapped[list["CreditTransactions"]] = relationship(
        "CreditTransactions", uselist=True, back_populates="user"
    )


class Boards(Base):
    __tablename__ = "boards"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id"], ["users.id"], ondelete="CASCADE", name="boards_owner_id_fkey"
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="boards_tenant_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="boards_pkey"),
        Index("idx_boards_owner", "owner_id"),
        Index("idx_boards_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    owner: Mapped["Users"] = relationship("Users", back_populates="boards")
    tenant: Mapped["Tenants"] = relationship("Tenants", back_populates="boards")
    board_members: Mapped[list["BoardMembers"]] = relationship(
        "BoardMembers", uselist=True, back_populates="board"
    )
    generations: Mapped[list["Generations"]] = relationship(
        "Generations", uselist=True, back_populates="board"
    )


class LoraModels(Base):
    __tablename__ = "lora_models"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="lora_models_tenant_id_fkey",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="lora_models_user_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="lora_models_pkey"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_model: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    trigger_word: Mapped[str | None] = mapped_column(String(100))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    is_public: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    tenant: Mapped["Tenants"] = relationship("Tenants", back_populates="lora_models")
    user: Mapped["Users"] = relationship("Users", back_populates="lora_models")


class BoardMembers(Base):
    __tablename__ = "board_members"
    __table_args__ = (
        CheckConstraint(
            "role::text = ANY (ARRAY["
            "'viewer'::character varying, 'editor'::character varying, "
            "'admin'::character varying]::text[])",
            name="board_members_role_check",
        ),
        ForeignKeyConstraint(
            ["board_id"],
            ["boards.id"],
            ondelete="CASCADE",
            name="board_members_board_id_fkey",
        ),
        ForeignKeyConstraint(["invited_by"], ["users.id"], name="board_members_invited_by_fkey"),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="board_members_user_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="board_members_pkey"),
        UniqueConstraint("board_id", "user_id", name="board_members_board_id_user_id_key"),
        Index("idx_board_members_board", "board_id"),
        Index("idx_board_members_user", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    board_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    invited_by: Mapped[UUID | None] = mapped_column(Uuid)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    board: Mapped["Boards"] = relationship("Boards", back_populates="board_members")
    users: Mapped["Users | None"] = relationship(
        "Users", foreign_keys=[invited_by], back_populates="board_members"
    )
    user: Mapped["Users"] = relationship(
        "Users", foreign_keys=[user_id], back_populates="board_members_"
    )


class Generations(Base):
    __tablename__ = "generations"
    __table_args__ = (
        CheckConstraint(
            "artifact_type::text = ANY (ARRAY["
            "'image'::character varying, 'video'::character varying, "
            "'audio'::character varying, 'text'::character varying, "
            "'lora'::character varying, 'model'::character varying"
            "]::text[])",
            name="generations_artifact_type_check",
        ),
        ForeignKeyConstraint(
            ["board_id"],
            ["boards.id"],
            ondelete="CASCADE",
            name="generations_board_id_fkey",
        ),
        ForeignKeyConstraint(
            ["parent_generation_id"],
            ["generations.id"],
            name="generations_parent_generation_id_fkey",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="generations_tenant_id_fkey",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="generations_user_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="generations_pkey"),
        Index("idx_generations_board", "board_id"),
        Index("idx_generations_lineage", "parent_generation_id"),
        Index("idx_generations_status", "status"),
        Index("idx_generations_tenant", "tenant_id"),
        Index("idx_generations_user", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    board_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    generator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'pending'::character varying")
    )
    storage_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    additional_files: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    output_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    parent_generation_id: Mapped[UUID | None] = mapped_column(Uuid)
    input_generation_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid()), server_default=text("'{}'::uuid[]")
    )
    external_job_id: Mapped[str | None] = mapped_column(String(255))
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default=text("0.0"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    board: Mapped["Boards"] = relationship("Boards", back_populates="generations")
    parent_generation: Mapped["Generations | None"] = relationship(
        "Generations",
        remote_side="Generations.id",
        back_populates="parent_generation_reverse",
    )
    parent_generation_reverse: Mapped[list["Generations"]] = relationship(
        "Generations",
        uselist=True,
        remote_side="Generations.parent_generation_id",
        back_populates="parent_generation",
    )
    tenant: Mapped["Tenants"] = relationship("Tenants", back_populates="generations")
    user: Mapped["Users"] = relationship("Users", back_populates="generations")
    credit_transactions: Mapped[list["CreditTransactions"]] = relationship(
        "CreditTransactions", uselist=True, back_populates="generation"
    )


class CreditTransactions(Base):
    __tablename__ = "credit_transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type::text = ANY (ARRAY["
            "'reserve'::character varying, 'finalize'::character varying, "
            "'refund'::character varying, 'purchase'::character varying, "
            "'grant'::character varying]::text[])",
            name="credit_transactions_transaction_type_check",
        ),
        ForeignKeyConstraint(
            ["generation_id"],
            ["generations.id"],
            name="credit_transactions_generation_id_fkey",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="credit_transactions_tenant_id_fkey",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="credit_transactions_user_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="credit_transactions_pkey"),
        Index("idx_credit_transactions_user", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    generation_id: Mapped[UUID | None] = mapped_column(Uuid)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP")
    )

    generation: Mapped["Generations | None"] = relationship(
        "Generations", back_populates="credit_transactions"
    )
    tenant: Mapped["Tenants"] = relationship("Tenants", back_populates="credit_transactions")
    user: Mapped["Users"] = relationship("Users", back_populates="credit_transactions")


# Expose for Alembic
target_metadata = Base.metadata
