"""Fal.ai video generators."""

from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .minimax_hailuo_2_3_pro_image_to_video import (
    FalMinimaxHailuo23ProImageToVideoGenerator,
)
from .sync_lipsync_v2 import FalSyncLipsyncV2Generator
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator

__all__ = [
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalMinimaxHailuo23ProImageToVideoGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeo31FirstLastFrameToVideoGenerator",
]
