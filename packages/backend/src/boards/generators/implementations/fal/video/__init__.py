"""Fal.ai video generators."""

from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .sora2_image_to_video import FalSora2ImageToVideoGenerator
from .sync_lipsync_v2 import FalSyncLipsyncV2Generator
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator

__all__ = [
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalSora2ImageToVideoGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeo31FirstLastFrameToVideoGenerator",
]
