"""Base classes for the artifact plugin system.

Defines BaseArtifactPlugin (abstract), PluginContext, and PluginResult.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from ..generators.artifacts import ArtifactTypeName


class PluginResult(BaseModel):
    """Result returned by a plugin after execution."""

    success: bool
    # If provided, replaces the artifact content bytes (for plugins that modify files)
    output_file_path: Path | None = None
    # If success=False and fail_generation=True, this message is stored in the generation record
    error_message: str | None = None
    # Whether a plugin failure should fail the entire generation
    fail_generation: bool = True
    # Optional metadata to attach to the artifact record
    metadata: dict | None = None


class PluginContext(BaseModel):
    """Context provided to plugins during execution."""

    # Local file path to the artifact (read/write access)
    file_path: Path

    # Artifact metadata
    artifact_type: ArtifactTypeName
    mime_type: str
    file_size_bytes: int

    # Generation metadata
    generation_id: str
    generator_name: str
    generator_inputs: dict  # The inputs passed to the generator (includes prompt, etc.)

    # Board context
    board_id: str

    # User/tenant context
    tenant_id: str
    user_id: str

    model_config = {"arbitrary_types_allowed": True}


class BaseArtifactPlugin(ABC):
    """Base class for artifact plugins.

    Plugins run after a generator produces an artifact but before the
    artifact is uploaded to remote storage. This enables post-processing
    operations that require access to the local file data.
    """

    # Unique identifier for the plugin
    name: str

    # Human-readable description
    description: str

    # Artifact types this plugin applies to (empty = all types)
    supported_artifact_types: list[ArtifactTypeName] = []

    @abstractmethod
    async def execute(self, context: PluginContext) -> PluginResult:
        """Execute the plugin on an artifact.

        Args:
            context: Full context about the artifact and generation

        Returns:
            PluginResult indicating success/failure and optional modifications
        """

    def supports_artifact_type(self, artifact_type: ArtifactTypeName) -> bool:
        """Check if this plugin supports the given artifact type."""
        if not self.supported_artifact_types:
            return True  # Empty list means all types
        return artifact_type in self.supported_artifact_types
