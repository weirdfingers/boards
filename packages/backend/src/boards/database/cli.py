#!/usr/bin/env python3
"""
CLI entry point for Boards database migrations.
"""

import sys
from pathlib import Path

import click

from alembic import command
from alembic.config import Config
from boards import __version__
from boards.logging import configure_logging, get_logger

logger = get_logger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Find alembic.ini in the package directory
    package_dir = Path(__file__).parent.parent.parent.parent
    alembic_ini = package_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    return Config(str(alembic_ini))


@click.group()
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
    help="Log level (default: info)",
)
@click.version_option(version=__version__, prog_name="boards-migrate")
def main(log_level: str) -> None:
    """Boards database migration management."""
    configure_logging(debug=(log_level == "debug"))


@main.command()
@click.argument("revision", default="head")
def upgrade(revision: str) -> None:
    """Upgrade database to a revision (default: head)."""
    try:
        config = get_alembic_config()
        logger.info("Upgrading database", revision=revision)
        command.upgrade(config, revision)
        logger.info("Database upgrade completed successfully")
    except Exception as e:
        logger.error("Database upgrade failed", error=str(e))
        sys.exit(1)


@main.command()
@click.argument("revision", default="-1")
def downgrade(revision: str) -> None:
    """Downgrade database to a revision (default: -1)."""
    try:
        config = get_alembic_config()
        logger.info("Downgrading database", revision=revision)
        command.downgrade(config, revision)
        logger.info("Database downgrade completed successfully")
    except Exception as e:
        logger.error("Database downgrade failed", error=str(e))
        sys.exit(1)


@main.command()
@click.option("-m", "--message", required=True, help="Revision message")
@click.option("--autogenerate/--no-autogenerate", default=True, help="Auto-generate migration")
def revision(message: str, autogenerate: bool) -> None:
    """Create a new migration revision."""
    try:
        config = get_alembic_config()
        logger.info("Creating new migration", message=message, autogenerate=autogenerate)
        command.revision(config, message=message, autogenerate=autogenerate)
        logger.info("Migration created successfully")
    except Exception as e:
        logger.error("Migration creation failed", error=str(e))
        sys.exit(1)


@main.command()
def current() -> None:
    """Show current database revision."""
    try:
        config = get_alembic_config()
        command.current(config)
    except Exception as e:
        logger.error("Failed to get current revision", error=str(e))
        sys.exit(1)


@main.command()
def history() -> None:
    """Show migration history."""
    try:
        config = get_alembic_config()
        command.history(config)
    except Exception as e:
        logger.error("Failed to get migration history", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
