#!/usr/bin/env python3
"""
CLI entry point for Boards background workers.

For auto-reload during development, use a file watcher like entr or nodemon:

    # Using entr (recommended):
    make dev-worker-watch

    # Or manually with entr:
    find packages/backend/src -name '*.py' | entr -r uv run boards-worker

    # Using nodemon:
    nodemon --watch packages/backend/src --exec "uv run boards-worker"
"""

import sys

import click

from boards import __version__
from boards.logging import configure_logging, get_logger

logger = get_logger(__name__)


def start_worker(
    processes: int,
    threads: int,
    queue_list: list[str],
    log_level: str,
) -> None:
    """Start the Dramatiq worker process."""
    # Configure logging
    configure_logging(debug=(log_level == "debug"))

    try:
        # Import workers to register them (if they exist)
        try:
            from boards.workers import actors  # noqa: F401
        except ImportError:
            logger.warning("No worker actors found - continuing with empty worker")

        # Start the worker
        from dramatiq.cli import main as dramatiq_main

        # Build dramatiq CLI args
        args = [
            "dramatiq",
            "boards.workers.actors",
            f"--processes={processes}",
            f"--threads={threads}",
        ]

        for queue in queue_list:
            args.extend(["--queues", queue])

        # Override sys.argv for dramatiq CLI
        original_argv = sys.argv
        sys.argv = args

        dramatiq_main()

    except KeyboardInterrupt:
        logger.info("Worker shutdown requested by user")
    except Exception as e:
        logger.error("Worker startup failed", error=str(e))
        sys.exit(1)
    finally:
        # Restore original argv
        sys.argv = original_argv


@click.command()
@click.option(
    "--processes",
    default=1,
    type=int,
    help="Number of worker processes (default: 1)",
)
@click.option(
    "--threads",
    default=1,
    type=int,
    help="Number of worker threads per process (default: 1)",
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
@click.version_option(version=__version__, prog_name="boards-worker")
def main(
    processes: int,
    threads: int,
    queues: str,
    log_level: str,
) -> None:
    """Start Boards background workers."""

    # Configure logging
    configure_logging(debug=(log_level == "debug"))

    queue_list = [q.strip() for q in queues.split(",")]

    logger.info(
        "Starting Boards workers",
        processes=processes,
        threads=threads,
        queues=queue_list,
        log_level=log_level,
    )

    start_worker(processes, threads, queue_list, log_level)


# meaningless
if __name__ == "__main__":
    main()
