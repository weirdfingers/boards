"""Dramatiq middleware for worker process initialization.

This module provides custom middleware for managing worker lifecycle,
particularly for loading generators and plugins during worker startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dramatiq.middleware import Middleware

from ..config import initialize_generator_api_keys, settings
from ..generators.loader import load_generators_from_config
from ..generators.registry import registry as generator_registry
from ..generators.resolution import set_plugin_executor
from ..logging import configure_logging, get_logger
from ..plugins.executor import ArtifactPluginExecutor
from ..plugins.loader import load_plugins_from_config
from ..plugins.registry import plugin_registry

if TYPE_CHECKING:
    from dramatiq import Broker, Worker

logger = get_logger(__name__)


class GeneratorLoaderMiddleware(Middleware):
    """Middleware to load generators and plugins when worker process starts.

    This ensures that generators and plugins are registered in each worker
    process's registry before any jobs are processed. Since Dramatiq uses
    multiprocessing, each worker process gets its own copy of the registries,
    so initialization must happen in each process.

    The before_worker_boot hook runs once per worker process at startup,
    before any actors are executed. Worker processes are long-running and
    reused across many jobs, so this initialization overhead happens only
    once per worker lifetime.
    """

    def before_worker_boot(self, broker: Broker, worker: Worker) -> None:
        """Load generators and plugins when worker process starts.

        Args:
            broker: The Dramatiq broker instance
            worker: The worker process instance
        """
        # Configure logging for this worker process (subprocess doesn't inherit parent's config)
        configure_logging(
            debug=settings.debug, google_logging_compat=settings.google_logging_compat
        )

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

        # Load artifact plugins
        load_plugins_from_config()

        plugin_names = plugin_registry.list_names()
        if plugin_names:
            executor = ArtifactPluginExecutor(
                registry=plugin_registry,
                plugin_timeout=settings.plugin_timeout,
                total_timeout=settings.plugin_total_timeout,
            )
            set_plugin_executor(executor)
            logger.info(
                "Plugins loaded in worker process",
                worker_id=id(worker),
                plugin_count=len(plugin_names),
                plugins=plugin_names,
            )
        else:
            set_plugin_executor(None)
            logger.info("No plugins configured")
