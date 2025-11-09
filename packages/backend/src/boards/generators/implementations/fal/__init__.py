"""Fal.ai provider generators."""

from . import audio, image, video
from .image import (
    FalFluxProUltraGenerator,
    FalNanoBananaEditGenerator,
    FalNanoBananaGenerator,
)
from .video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
    FalVeo31FirstLastFrameToVideoGenerator,
)

__all__ = [
    # Image generators
    "FalFluxProUltraGenerator",
    "FalNanoBananaGenerator",
    "FalNanoBananaEditGenerator",
    # Video generators
    "FalVeo31FirstLastFrameToVideoGenerator",
    "FalNanoBananaEditGenerator",
    "FalNanoBananaGenerator",
    # Video generators
    "FalKlingVideoV25TurboProTextToVideoGenerator",
]
