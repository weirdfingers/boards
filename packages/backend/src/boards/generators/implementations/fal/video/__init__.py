"""Fal.ai video generators."""

from .fal_sora_2_text_to_video import FalSora2TextToVideoGenerator
from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .sync_lipsync_v2 import FalSyncLipsyncV2Generator
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator

__all__ = [
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalSora2TextToVideoGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeo31FirstLastFrameToVideoGenerator",
]
