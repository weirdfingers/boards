#!/usr/bin/env python3
"""
Main CLI entry point for Boards backend server.
"""

import os
import sys

import click
import uvicorn

from boards import __version__
from boards.logging import configure_logging, get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="boards")
def cli() -> None:
    """Boards CLI - manage server, database, and tenants."""
    pass


@cli.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind to (default: 0.0.0.0)",
)
@click.option(
    "--port",
    default=8088,
    type=int,
    help="Port to bind to (default: 8088)",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload for development",
)
@click.option(
    "--workers",
    default=1,
    type=int,
    help="Number of worker processes (default: 1)",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
    help="Log level (default: info)",
)
def serve(
    host: str,
    port: int,
    reload: bool,
    workers: int,
    log_level: str,
) -> None:
    """Start the Boards API server."""

    # Configure logging
    configure_logging(debug=(log_level == "debug"))

    logger.info(
        "Starting Boards API server",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )

    # Set environment variables for app configuration when using reload/workers
    # This ensures the app imports with the correct settings
    if log_level == "debug":
        os.environ["BOARDS_DEBUG"] = "true"
        os.environ["BOARDS_LOG_LEVEL"] = "debug"
    else:
        os.environ.setdefault("BOARDS_DEBUG", "false")
        os.environ.setdefault("BOARDS_LOG_LEVEL", log_level)

    try:
        # When using reload or multiple workers, pass app as import string
        if reload or workers > 1:
            uvicorn.run(
                "boards.api.app:app",
                host=host,
                port=port,
                reload=reload,
                workers=(workers if not reload else 1),  # reload doesn't work with multiple workers
                log_level=log_level,
                access_log=True,
            )
        else:
            # Import app directly when not using reload/workers
            from boards.api.app import app

            uvicorn.run(
                app,
                host=host,
                port=port,
                reload=reload,
                workers=workers,
                log_level=log_level,
                access_log=True,
            )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        sys.exit(1)


@cli.group()
def tenant() -> None:
    """Manage tenants in the database."""
    pass


@tenant.command("create")
@click.option(
    "--name",
    required=True,
    help="Display name for the tenant",
)
@click.option(
    "--slug",
    required=True,
    help="Unique slug for the tenant (used in URLs)",
)
@click.option(
    "--sample-data",
    is_flag=True,
    default=False,
    help="Include sample data for the tenant",
)
def create_tenant(
    name: str,
    slug: str,
    sample_data: bool,
) -> None:
    """Create a new tenant in the database."""
    import asyncio

    from boards.database.connection import get_async_session
    from boards.database.seed_data import seed_tenant_with_data

    configure_logging()

    async def do_create():
        async with get_async_session() as db:
            try:
                tenant_id = await seed_tenant_with_data(
                    db,
                    tenant_name=name,
                    tenant_slug=slug,
                    include_sample_data=sample_data,
                )
                logger.info(
                    "Tenant created successfully",
                    tenant_id=str(tenant_id),
                    name=name,
                    slug=slug,
                )
                click.echo(f"✓ Tenant created: {tenant_id}")
                click.echo(f"  Name: {name}")
                click.echo(f"  Slug: {slug}")
                if sample_data:
                    click.echo("  Sample data: included")
            except Exception as e:
                logger.error("Failed to create tenant", error=str(e))
                click.echo(f"✗ Error creating tenant: {e}", err=True)
                sys.exit(1)

    asyncio.run(do_create())


@tenant.command("list")
def list_tenants() -> None:
    """List all tenants in the database."""
    import asyncio

    from sqlalchemy import select

    from boards.database.connection import get_async_session
    from boards.dbmodels import Tenants

    configure_logging()

    async def do_list():
        async with get_async_session() as db:
            try:
                stmt = select(Tenants).order_by(Tenants.created_at)
                result = await db.execute(stmt)
                tenants = result.scalars().all()

                if not tenants:
                    click.echo("No tenants found.")
                else:
                    click.echo(f"Found {len(tenants)} tenant(s):")
                    click.echo()
                    for t in tenants:
                        click.echo(f"  ID: {t.id}")
                        click.echo(f"  Name: {t.name}")
                        click.echo(f"  Slug: {t.slug}")
                        click.echo(f"  Created: {t.created_at}")
                        click.echo()
            except Exception as e:
                logger.error("Failed to list tenants", error=str(e))
                click.echo(f"✗ Error listing tenants: {e}", err=True)
                sys.exit(1)

    asyncio.run(do_list())


@tenant.command("audit")
@click.option(
    "--tenant-slug",
    help="Slug of specific tenant to audit (audits all if not specified)",
)
@click.option(
    "--output-format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format (default: table)",
)
def audit_tenant_isolation(tenant_slug: str | None, output_format: str) -> None:
    """Audit tenant isolation for security validation."""
    import asyncio
    import json

    from sqlalchemy import select

    from boards.database.connection import get_async_session
    from boards.dbmodels import Tenants
    from boards.tenant_isolation import TenantIsolationValidator

    configure_logging()

    async def do_audit():
        async with get_async_session() as db:
            try:
                validator = TenantIsolationValidator(db)

                # Determine which tenants to audit
                if tenant_slug:
                    stmt = select(Tenants).where(Tenants.slug == tenant_slug)
                    result = await db.execute(stmt)
                    tenant = result.scalar_one_or_none()
                    if not tenant:
                        click.echo(f"✗ Tenant '{tenant_slug}' not found", err=True)
                        sys.exit(1)
                    tenants_to_audit = [tenant]
                else:
                    stmt = select(Tenants).order_by(Tenants.created_at)
                    result = await db.execute(stmt)
                    tenants_to_audit = result.scalars().all()

                if not tenants_to_audit:
                    click.echo("No tenants found to audit.")
                    return

                # Perform audits
                audit_results = []
                for tenant in tenants_to_audit:
                    click.echo(f"🔍 Auditing tenant: {tenant.slug}")
                    audit_result = await validator.audit_tenant_isolation(tenant.id)
                    audit_results.append(audit_result)

                # Output results
                if output_format == "json":
                    click.echo(json.dumps(audit_results, indent=2))
                else:
                    _display_audit_results_table(audit_results)

            except Exception as e:
                logger.error("Failed to audit tenant isolation", error=str(e))
                click.echo(f"✗ Error auditing tenants: {e}", err=True)
                sys.exit(1)

    def _display_audit_results_table(results):
        """Display audit results in table format."""
        click.echo("\n" + "=" * 80)
        click.echo("TENANT ISOLATION AUDIT RESULTS")
        click.echo("=" * 80)

        for result in results:
            violations = result["isolation_violations"]
            stats = result["statistics"]

            click.echo(f"\n📋 Tenant: {result['tenant_id']}")
            click.echo(f"   Audit Time: {result['audit_timestamp']}")

            # Statistics
            click.echo("\n📊 Statistics:")
            click.echo(f"   Users: {stats.get('users_count', 0)}")
            click.echo(f"   Boards: {stats.get('boards_count', 0)}")
            click.echo(f"   Generations: {stats.get('generations_count', 0)}")
            click.echo(f"   Board Memberships: {stats.get('board_memberships_count', 0)}")

            # Violations
            if violations:
                click.echo(f"\n⚠️  Isolation Violations ({len(violations)}):")
                for i, violation in enumerate(violations, 1):
                    click.echo(f"   {i}. {violation['type']}: {violation['description']}")
            else:
                click.echo("\n✅ No isolation violations found")

            # Recommendations
            click.echo("\n💡 Recommendations:")
            for rec in result["recommendations"]:
                click.echo(f"   • {rec}")

            if result != results[-1]:  # Not the last result
                click.echo("\n" + "-" * 60)

        click.echo("\n" + "=" * 80)

    asyncio.run(do_audit())


@cli.command()
def seed() -> None:
    """Seed the database with initial data."""
    import asyncio

    from boards.database.connection import get_async_session
    from boards.database.seed_data import seed_initial_data

    configure_logging()

    async def do_seed():
        async with get_async_session() as db:
            try:
                await seed_initial_data(db)
                click.echo("✓ Database seeded successfully")
            except Exception as e:
                logger.error("Failed to seed database", error=str(e))
                click.echo(f"✗ Error seeding database: {e}", err=True)
                sys.exit(1)

    asyncio.run(do_seed())


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    cli()
