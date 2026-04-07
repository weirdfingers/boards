"""Plugin registry for managing artifact plugins."""

from __future__ import annotations

from ..generators.artifacts import ArtifactTypeName
from ..logging import get_logger
from .base import BaseArtifactPlugin

logger = get_logger(__name__)


class ArtifactPluginRegistry:
    """Manages registered artifact plugins.

    Plugins are stored in insertion order, which determines execution order.
    """

    def __init__(self) -> None:
        self._plugins: list[BaseArtifactPlugin] = []

    def register(self, plugin: BaseArtifactPlugin) -> None:
        """Register a plugin instance.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        if any(p.name == plugin.name for p in self._plugins):
            raise ValueError(f"Plugin with name '{plugin.name}' already registered")
        self._plugins.append(plugin)
        logger.info("Registered plugin", plugin_name=plugin.name)

    def get_plugins_for_artifact(
        self, artifact_type: ArtifactTypeName
    ) -> list[BaseArtifactPlugin]:
        """Get ordered list of plugins that apply to the given artifact type."""
        return [p for p in self._plugins if p.supports_artifact_type(artifact_type)]

    def list_all(self) -> list[BaseArtifactPlugin]:
        """List all registered plugins in order."""
        return list(self._plugins)

    def list_names(self) -> list[str]:
        """List all registered plugin names."""
        return [p.name for p in self._plugins]

    def unregister(self, name: str) -> bool:
        """Remove a plugin by name. Returns True if found and removed."""
        for i, p in enumerate(self._plugins):
            if p.name == name:
                self._plugins.pop(i)
                return True
        return False

    def clear(self) -> None:
        """Remove all registered plugins."""
        self._plugins.clear()

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return any(p.name == name for p in self._plugins)


# Global registry instance
plugin_registry = ArtifactPluginRegistry()
