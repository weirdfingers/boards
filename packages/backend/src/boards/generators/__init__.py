"""
Boards generators system for integrating AI generation services.

This package provides a simple, type-safe way to define and use AI generators
that produce various types of artifacts (images, videos, audio, text, etc.).

Key components:
- BaseGenerator: Abstract base class for all generators
- Artifact types: Pydantic models for different content types
- Registry: System for discovering and managing generators
- Resolution utilities: For converting artifacts to files for provider SDKs

Example usage:
    from boards.generators import registry
    from boards.generators.implementations.replicate.image.flux_pro import ReplicateFluxProGenerator

    # Get available generators
    image_generators = registry.list_by_artifact_type("image")

    # Use a specific generator
    flux = registry.get("replicate-flux-pro")
    result = await flux.generate(inputs)
"""

from .artifacts import (
    AudioArtifact,
    ImageArtifact,
    LoRArtifact,
    TextArtifact,
    VideoArtifact,
)
from .base import BaseGenerator
from .registry import GeneratorRegistry, registry
from .resolution import (
    resolve_artifact,
    store_audio_result,
    store_image_result,
    store_video_result,
)

__all__ = [
    # Core classes
    "BaseGenerator",
    "GeneratorRegistry",
    "registry",
    # Artifact types
    "AudioArtifact",
    "VideoArtifact",
    "ImageArtifact",
    "TextArtifact",
    "LoRArtifact",
    # Utilities
    "resolve_artifact",
    "store_image_result",
    "store_video_result",
    "store_audio_result",
]
