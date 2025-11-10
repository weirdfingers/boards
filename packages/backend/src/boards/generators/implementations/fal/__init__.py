"""Fal.ai provider generators."""

from . import audio, image, video
from .image import (
    FalFluxProUltraGenerator,
    FalNanoBananaEditGenerator,
    FalNanoBananaGenerator,
)
from .video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
    FalSyncLipsyncV2Generator,
    FalVeo31FirstLastFrameToVideoGenerator,
)

# Maintain alphabetical order
__all__ = [
    # Image generators
    "FalFluxProUltraGenerator",
    "FalNanoBananaEditGenerator",
    "FalNanoBananaGenerator",
    # Video generators
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeo31FirstLastFrameToVideoGenerator",
]
