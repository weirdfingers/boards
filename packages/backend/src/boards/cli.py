#!/usr/bin/env python3
"""
Main CLI entry point for Boards backend server.
"""

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
    default=8000,
    type=int,
    help="Port to bind to (default: 8000)",
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

    # Import app after logging is configured
    from boards.api.app import app

    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            workers=(
                workers if not reload else 1
            ),  # reload doesn't work with multiple workers
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


if __name__ == "__main__":
    cli()
