"""Fal.ai video generators."""

from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator

__all__ = [
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalVeo31FirstLastFrameToVideoGenerator",
]
