#!/usr/bin/env python3
"""
Combined worker entrypoint with health check server.

This module starts both:
1. A minimal HTTP health check server (for Cloud Run compatibility)
2. The dramatiq-gevent worker (for job processing)

Usage:
    python -m boards.workers.worker_main [options]

Or via the boards-worker-health console script.
"""

import os
import subprocess
import sys

import click

from boards import __version__
from boards.logging import configure_logging, get_logger
from boards.workers.health import start_health_server_thread

logger = get_logger(__name__)


@click.command()
@click.option(
    "--processes",
    default=1,
    type=int,
    help="Number of worker processes (default: 1)",
)
@click.option(
    "--threads",
    default=50,
    type=int,
    help="Number of worker threads per process (default: 50)",
)
@click.option(
    "--queues",
    default="boards-jobs",
    help="Comma-separated list of queues to process (default: boards-jobs)",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
    help="Log level (default: info)",
)
@click.option(
    "--health-port",
    default=None,
    type=int,
    help="Health check server port (default: PORT env var or 8080)",
)
@click.version_option(version=__version__, prog_name="boards-worker-health")
def main(
    processes: int,
    threads: int,
    queues: str,
    log_level: str,
    health_port: int | None,
) -> None:
    """Start Boards worker with integrated health check server."""
    # Configure logging
    configure_logging(debug=(log_level == "debug"))

    # Determine health port
    if health_port is None:
        health_port = int(os.environ.get("PORT", 8080))

    queue_list = [q.strip() for q in queues.split(",")]

    logger.info(
        "Starting Boards worker with health server",
        processes=processes,
        threads=threads,
        queues=queue_list,
        health_port=health_port,
        log_level=log_level,
    )

    # Start health server in background thread
    start_health_server_thread(health_port)
    logger.info("Health check server running", port=health_port)

    # Build dramatiq-gevent command
    cmd = [
        "dramatiq-gevent",
        "boards.workers.actors:broker",
        f"--processes={processes}",
        f"--threads={threads}",
    ]

    for queue in queue_list:
        cmd.extend(["--queues", queue])

    logger.info("Starting dramatiq-gevent worker", cmd=" ".join(cmd))

    # Run dramatiq-gevent (blocking)
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
