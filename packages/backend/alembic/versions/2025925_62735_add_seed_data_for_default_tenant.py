"""Add seed data for default tenant

This migration creates a default tenant for single-tenant deployments.
It can be customized via environment variables:

- BOARDS_TENANT_NAME: Display name for the default tenant (default: "Default Tenant")
- BOARDS_TENANT_SLUG: Slug for the default tenant (default: "default")

Revision ID: 553dc6a50a20
Revises: 20250101_000000_initial_schema
Create Date: 2025-09-25 06:27:35.976189

"""
import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '553dc6a50a20'
down_revision: str | Sequence[str] | None = '20250101_000000_initial_schema'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema and seed default tenant."""
    # Get configuration from environment variables
    tenant_name = os.getenv("BOARDS_TENANT_NAME", "Default Tenant")
    tenant_slug = os.getenv("BOARDS_TENANT_SLUG", "default")

    # Only create the default tenant if it doesn't exist
    # This allows the migration to be run multiple times safely
    connection = op.get_bind()

    # Check if tenant already exists
    existing_tenant = connection.execute(
        sa.text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": tenant_slug}
    ).fetchone()

    if not existing_tenant:
        # Insert the default tenant
        connection.execute(
            sa.text("""
                INSERT INTO tenants (name, slug, settings, created_at, updated_at)
                VALUES (:name, :slug, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "name": tenant_name,
                "slug": tenant_slug,
            }
        )
        print(f"Created default tenant: {tenant_name} (slug: {tenant_slug})")
    else:
        print(f"Default tenant already exists: {tenant_slug}")


def downgrade() -> None:
    """Downgrade schema and remove seeded data."""
    # Get configuration from environment variables (same as upgrade)
    tenant_slug = os.getenv("BOARDS_TENANT_SLUG", "default")

    # Remove the default tenant
    # WARNING: This will cascade delete all related data!
    connection = op.get_bind()

    result = connection.execute(
        sa.text("DELETE FROM tenants WHERE slug = :slug"),
        {"slug": tenant_slug}
    )

    if result.rowcount > 0:
        print(f"Removed default tenant: {tenant_slug}")
    else:
        print(f"Default tenant not found: {tenant_slug}")

    # Note: Due to CASCADE constraints, this will also remove:
    # - All users in this tenant
    # - All boards in this tenant
    # - All generations in this tenant
    # - All provider configs for this tenant
    print("WARNING: All tenant data has been removed due to CASCADE constraints")
