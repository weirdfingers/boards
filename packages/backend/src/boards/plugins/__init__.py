"""Artifact plugin system for post-processing generated content.

Plugins run after a generator produces an artifact but before it is
uploaded to remote storage. This enables operations like C2PA signing,
watermarking, format conversion, and content analysis.
"""

from .base import BaseArtifactPlugin, PluginContext, PluginResult
from .exceptions import PluginExecutionError, PluginLoadError, PluginTimeoutError
from .executor import ArtifactPluginExecutor
from .loader import load_plugins_from_config
from .registry import ArtifactPluginRegistry, plugin_registry

__all__ = [
    # Base classes
    "BaseArtifactPlugin",
    "PluginContext",
    "PluginResult",
    # Registry
    "ArtifactPluginRegistry",
    "plugin_registry",
    # Executor
    "ArtifactPluginExecutor",
    # Loader
    "load_plugins_from_config",
    # Exceptions
    "PluginExecutionError",
    "PluginLoadError",
    "PluginTimeoutError",
]
