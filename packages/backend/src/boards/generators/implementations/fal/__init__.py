"""Fal.ai provider generators."""

from . import audio, image
from .image import (
    FalFluxProUltraGenerator,
    FalNanoBananaEditGenerator,
    FalNanoBananaGenerator,
)
from .video import FalVeo31FirstLastFrameToVideoGenerator

__all__ = [
    # Image generators
    "FalFluxProUltraGenerator",
    "FalNanoBananaGenerator",
    "FalNanoBananaEditGenerator",
    # Video generators
    "FalVeo31FirstLastFrameToVideoGenerator",
]
