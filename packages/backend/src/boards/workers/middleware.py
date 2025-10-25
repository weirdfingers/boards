"""Dramatiq middleware for worker process initialization.

This module provides custom middleware for managing worker lifecycle,
particularly for loading generators during worker startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dramatiq.middleware import Middleware

from ..config import initialize_generator_api_keys
from ..generators.loader import load_generators_from_config
from ..generators.registry import registry as generator_registry
from ..logging import get_logger

if TYPE_CHECKING:
    from dramatiq import Broker, Worker

logger = get_logger(__name__)


class GeneratorLoaderMiddleware(Middleware):
    """Middleware to load generators when worker process starts.

    This ensures that generators are registered in each worker process's
    registry before any jobs are processed. Since Dramatiq uses multiprocessing,
    each worker process gets its own copy of the registry, so initialization
    must happen in each process.

    The before_worker_boot hook runs once per worker process at startup,
    before any actors are executed. Worker processes are long-running and
    reused across many jobs, so this initialization overhead happens only
    once per worker lifetime.
    """

    def before_worker_boot(self, broker: Broker, worker: Worker) -> None:
        """Load generators when worker process starts.

        Args:
            broker: The Dramatiq broker instance
            worker: The worker process instance
        """
        logger.info("Loading generators in worker process", worker_id=id(worker))

        # Initialize generator API keys before loading generators
        initialize_generator_api_keys()
        logger.info("Generator API keys initialized in worker process")

        load_generators_from_config()

        logger.info(
            "Generators loaded in worker process",
            worker_id=id(worker),
            generator_count=len(generator_registry.list_names()),
            generators=generator_registry.list_names(),
        )
