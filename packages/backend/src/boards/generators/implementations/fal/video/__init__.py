"""Fal.ai video generators."""

from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .sora_2_text_to_video_pro import FalSora2TextToVideoProGenerator
from .sync_lipsync_v2 import FalSyncLipsyncV2Generator
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator

__all__ = [
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalSora2TextToVideoProGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeo31FirstLastFrameToVideoGenerator",
]
