#!/usr/bin/env python3
"""
CLI entry point for Boards background workers.
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
    # Configure logging (important: when using --watch, this runs in a subprocess)
    configure_logging(debug=(log_level == "debug"))

    try:
        # Import workers to register them (if they exist)
        try:
            from boards.workers import actors  # noqa
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
@click.option(
    "--watch",
    is_flag=True,
    help="Auto-reload when source files change (development only)",
)
@click.version_option(version=__version__, prog_name="boards-worker")
def main(
    processes: int,
    threads: int,
    queues: str,
    log_level: str,
    watch: bool,
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
        watch=watch,
    )

    if watch:
        # Use watchfiles to auto-reload on file changes (development only)
        try:
            from watchfiles import run_process
        except ImportError:
            logger.error("watchfiles not installed - install with: uv add --dev watchfiles")
            sys.exit(1)

        import pathlib

        # Watch the boards package directory
        watch_path = pathlib.Path(__file__).parent.parent
        logger.info("Auto-reload enabled - watching for file changes", path=str(watch_path))

        # run_process will restart the worker when files change
        # It kills the entire process tree (parent + all worker children)
        run_process(
            watch_path,
            target=start_worker,
            args=(processes, threads, queue_list, log_level),
        )
    else:
        # Normal mode - just start the worker
        start_worker(processes, threads, queue_list, log_level)


if __name__ == "__main__":
    main()
