"""Fal.ai video generators."""

from .creatify_lipsync import FalCreatifyLipsyncGenerator
from .fal_pixverse_lipsync import FalPixverseLipsyncGenerator
from .infinitalk import FalInfinitalkGenerator
from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .sora_2_text_to_video_pro import FalSora2TextToVideoProGenerator
from .sync_lipsync_v2 import FalSyncLipsyncV2Generator
from .sync_lipsync_v2_pro import FalSyncLipsyncV2ProGenerator
from .veed_lipsync import FalVeedLipsyncGenerator
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator
from .veo31_image_to_video import FalVeo31ImageToVideoGenerator
from .veo31_reference_to_video import FalVeo31ReferenceToVideoGenerator

__all__ = [
    "FalInfinitalkGenerator",
    "FalCreatifyLipsyncGenerator",
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalPixverseLipsyncGenerator",
    "FalSora2TextToVideoProGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeedLipsyncGenerator",
    "FalSyncLipsyncV2ProGenerator",
    "FalVeo31FirstLastFrameToVideoGenerator",
    "FalVeo31ImageToVideoGenerator",
    "FalVeo31ReferenceToVideoGenerator",
]
