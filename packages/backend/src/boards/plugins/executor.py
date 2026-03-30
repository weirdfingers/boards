"""Plugin executor that runs plugins on artifacts in sequence."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from ..generators.artifacts import ArtifactTypeName
from ..logging import get_logger
from .base import BaseArtifactPlugin, PluginContext, PluginResult
from .exceptions import PluginExecutionError, PluginTimeoutError
from .registry import ArtifactPluginRegistry

logger = get_logger(__name__)


class ArtifactPluginExecutor:
    """Executes plugins on artifacts in the worker context.

    Plugins run in the order they appear in the registry. Each plugin
    receives a PluginContext and returns a PluginResult. If a plugin
    fails with fail_generation=True, the entire generation is failed.
    """

    def __init__(
        self,
        registry: ArtifactPluginRegistry,
        plugin_timeout: float | None = 60.0,
        total_timeout: float | None = 300.0,
    ) -> None:
        self.registry = registry
        self.plugin_timeout = plugin_timeout
        self.total_timeout = total_timeout

    async def execute_plugins(
        self,
        file_path: Path,
        context: PluginContext,
    ) -> tuple[Path, list[PluginResult]]:
        """Execute all applicable plugins on an artifact.

        Args:
            file_path: Path to the artifact file
            context: Plugin execution context

        Returns:
            Tuple of (final_file_path, list_of_results)

        Raises:
            PluginExecutionError: If a plugin fails with fail_generation=True
            PluginTimeoutError: If a plugin or total pipeline exceeds timeout
        """
        plugins = self.registry.get_plugins_for_artifact(context.artifact_type)
        if not plugins:
            return file_path, []

        results: list[PluginResult] = []
        current_path = file_path
        total_start = time.monotonic()

        for plugin in plugins:
            # Check total timeout
            if self.total_timeout is not None:
                elapsed = time.monotonic() - total_start
                if elapsed >= self.total_timeout:
                    raise PluginTimeoutError(
                        plugin_name=plugin.name,
                        timeout_seconds=self.total_timeout,
                    )

            # Update context with current file path
            context.file_path = current_path

            logger.info(
                "executing_artifact_plugin",
                plugin_name=plugin.name,
                generation_id=context.generation_id,
                artifact_type=context.artifact_type,
            )

            result = await self._execute_single(plugin, context)
            results.append(result)

            if not result.success:
                logger.warning(
                    "plugin_execution_failed",
                    plugin_name=plugin.name,
                    error_message=result.error_message,
                    fail_generation=result.fail_generation,
                )
                if result.fail_generation:
                    raise PluginExecutionError(
                        plugin_name=plugin.name,
                        error_message=result.error_message,
                    )

            # Update path if plugin produced a new file
            if result.output_file_path:
                current_path = result.output_file_path

        return current_path, results

    async def _execute_single(
        self, plugin: BaseArtifactPlugin, context: PluginContext
    ) -> PluginResult:
        """Execute a single plugin with optional timeout."""
        start = time.monotonic()
        try:
            if self.plugin_timeout is not None:
                result = await asyncio.wait_for(
                    plugin.execute(context),
                    timeout=self.plugin_timeout,
                )
            else:
                result = await plugin.execute(context)

            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "plugin_execution_complete",
                plugin_name=plugin.name,
                generation_id=context.generation_id,
                artifact_type=context.artifact_type,
                success=result.success,
                duration_ms=round(elapsed_ms, 1),
            )
            return result

        except asyncio.TimeoutError:
            raise PluginTimeoutError(
                plugin_name=plugin.name,
                timeout_seconds=self.plugin_timeout or 0,
            )
        except PluginTimeoutError:
            raise
        except PluginExecutionError:
            raise
        except Exception as e:
            raise PluginExecutionError(
                plugin_name=plugin.name,
                error_message=f"Unexpected error: {e}",
            ) from e

    def has_plugins_for(self, artifact_type: ArtifactTypeName) -> bool:
        """Check if there are any plugins registered for the given artifact type."""
        return len(self.registry.get_plugins_for_artifact(artifact_type)) > 0
