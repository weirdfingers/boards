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


@click.command()
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
@click.version_option(version=__version__, prog_name="boards-server")
def main(
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


if __name__ == "__main__":
    main()
