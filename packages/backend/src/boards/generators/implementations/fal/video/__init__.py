"""Fal.ai video generators."""

from .bytedance_seedance_v1_pro_text_to_video import (
    FalBytedanceSeedanceV1ProTextToVideoGenerator,
)
from .creatify_lipsync import FalCreatifyLipsyncGenerator
from .fal_bytedance_seedance_v1_pro_image_to_video import (
    FalBytedanceSeedanceV1ProImageToVideoGenerator,
)
from .fal_minimax_hailuo_02_standard_text_to_video import (
    FalMinimaxHailuo02StandardTextToVideoGenerator,
)
from .fal_pixverse_lipsync import FalPixverseLipsyncGenerator
from .fal_sora_2_text_to_video import FalSora2TextToVideoGenerator
from .infinitalk import FalInfinitalkGenerator
from .kling_video_ai_avatar_v2_pro import FalKlingVideoAiAvatarV2ProGenerator
from .kling_video_ai_avatar_v2_standard import (
    FalKlingVideoAiAvatarV2StandardGenerator,
)
from .kling_video_v2_5_turbo_pro_image_to_video import (
    FalKlingVideoV25TurboProImageToVideoGenerator,
)
from .kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
)
from .minimax_hailuo_2_3_pro_image_to_video import (
    FalMinimaxHailuo23ProImageToVideoGenerator,
)
from .sora2_image_to_video import FalSora2ImageToVideoGenerator
from .sora_2_image_to_video_pro import FalSora2ImageToVideoProGenerator
from .sora_2_text_to_video_pro import FalSora2TextToVideoProGenerator
from .sync_lipsync_v2 import FalSyncLipsyncV2Generator
from .sync_lipsync_v2_pro import FalSyncLipsyncV2ProGenerator
from .veed_fabric_1_0 import FalVeedFabric10Generator
from .veed_lipsync import FalVeedLipsyncGenerator
from .veo3 import FalVeo3Generator
from .veo31 import FalVeo31Generator
from .veo31_fast import FalVeo31FastGenerator
from .veo31_fast_image_to_video import FalVeo31FastImageToVideoGenerator
from .veo31_first_last_frame_to_video import FalVeo31FirstLastFrameToVideoGenerator
from .veo31_image_to_video import FalVeo31ImageToVideoGenerator
from .veo31_reference_to_video import FalVeo31ReferenceToVideoGenerator
from .wan_25_preview_image_to_video import FalWan25PreviewImageToVideoGenerator
from .wan_25_preview_text_to_video import FalWan25PreviewTextToVideoGenerator
from .wan_pro_image_to_video import FalWanProImageToVideoGenerator

__all__ = [
    "FalInfinitalkGenerator",
    "FalCreatifyLipsyncGenerator",
    "FalBytedanceSeedanceV1ProImageToVideoGenerator",
    "FalBytedanceSeedanceV1ProTextToVideoGenerator",
    "FalKlingVideoAiAvatarV2ProGenerator",
    "FalKlingVideoAiAvatarV2StandardGenerator",
    "FalKlingVideoV25TurboProImageToVideoGenerator",
    "FalKlingVideoV25TurboProTextToVideoGenerator",
    "FalPixverseLipsyncGenerator",
    "FalSora2TextToVideoProGenerator",
    "FalSora2TextToVideoGenerator",
    "FalMinimaxHailuo02StandardTextToVideoGenerator",
    "FalMinimaxHailuo23ProImageToVideoGenerator",
    "FalSora2ImageToVideoGenerator",
    "FalSora2ImageToVideoProGenerator",
    "FalSyncLipsyncV2Generator",
    "FalVeedFabric10Generator",
    "FalVeedLipsyncGenerator",
    "FalSyncLipsyncV2ProGenerator",
    "FalVeo3Generator",
    "FalVeo31Generator",
    "FalVeo31FastGenerator",
    "FalVeo31FastImageToVideoGenerator",
    "FalVeo31FirstLastFrameToVideoGenerator",
    "FalVeo31ImageToVideoGenerator",
    "FalVeo31ReferenceToVideoGenerator",
    "FalWan25PreviewImageToVideoGenerator",
    "FalWan25PreviewTextToVideoGenerator",
    "FalWanProImageToVideoGenerator",
]
