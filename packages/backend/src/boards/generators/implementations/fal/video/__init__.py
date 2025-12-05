"""Fal.ai video generators."""

from .infinitalk import FalInfinitalkGenerator
from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .sync_lipsync_v2 import FalSyncLipsyncV2Generator
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator
from .veo31_image_to_video import FalVeo31ImageToVideoGenerator
from .veo31_reference_to_video import FalVeo31ReferenceToVideoGenerator

__all__ = [
    "FalInfinitalkGenerator",
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeo31FirstLastFrameToVideoGenerator",
    "FalVeo31ImageToVideoGenerator",
    "FalVeo31ReferenceToVideoGenerator",
]
