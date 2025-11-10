"""
fal.ai sync-lipsync v2 video generator.

Generates realistic lip-synchronization animations from audio and video inputs
using fal.ai's sync-lipsync/v2 model. Supports advanced audio/video duration
mismatch handling with multiple sync modes.

Based on Fal AI's fal-ai/sync-lipsync/v2 model.
See: https://fal.ai/models/fal-ai/sync-lipsync/v2
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, VideoArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class SyncLipsyncV2Input(BaseModel):
    """Input schema for sync-lipsync v2.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    video: VideoArtifact = Field(description="Input video for lip-sync animation")
    audio: AudioArtifact = Field(description="Audio to synchronize with the video")
    model: Literal["lipsync-2", "lipsync-2-pro"] = Field(
        default="lipsync-2",
        description="Model selection; pro version costs ~1.67x more",
    )
    sync_mode: Literal["cut_off", "loop", "bounce", "silence", "remap"] = Field(
        default="cut_off",
        description="Handling method when audio/video durations mismatch",
    )


class FalSyncLipsyncV2Generator(BaseGenerator):
    """Generator for realistic lip-synchronization animations."""

    name = "fal-sync-lipsync-v2"
    description = "Fal: sync-lipsync v2 - Realistic lip-sync animation with audio"
    artifact_type = "video"

    def get_input_schema(self) -> type[SyncLipsyncV2Input]:
        """Return the input schema for this generator."""
        return SyncLipsyncV2Input

    async def generate(
        self, inputs: SyncLipsyncV2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate lip-synced video using fal.ai sync-lipsync/v2."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalSyncLipsyncV2Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload video and audio artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        # Upload video and audio separately
        video_urls = await upload_artifacts_to_fal([inputs.video], context)
        audio_urls = await upload_artifacts_to_fal([inputs.audio], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "video_url": video_urls[0],
            "audio_url": audio_urls[0],
            "model": inputs.model,
            "sync_mode": inputs.sync_mode,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/sync-lipsync/v2",
            arguments=arguments,
        )

        # Store external job ID
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates
        from .....progress.models import ProgressUpdate

        event_count = 0
        async for event in handler.iter_events(with_logs=True):
            event_count += 1
            # Sample every 3rd event to avoid spam
            if event_count % 3 == 0:
                # Extract logs if available
                logs = getattr(event, "logs", None)
                if logs:
                    # Join log entries into a single message
                    if isinstance(logs, list):
                        message = " | ".join(str(log) for log in logs if log)
                    else:
                        message = str(logs)

                    if message:
                        await context.publish_progress(
                            ProgressUpdate(
                                job_id=handler.request_id,
                                status="processing",
                                progress=50.0,  # Approximate mid-point progress
                                phase="processing",
                                message=message,
                            )
                        )

        # Get final result
        result = await handler.get()

        # Extract video from result
        # fal.ai returns: {"video": {"url": "...", "content_type": "video/mp4", ...}}
        video_data = result.get("video")

        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract format from content_type (e.g., "video/mp4" -> "mp4")
        content_type = video_data.get("content_type", "video/mp4")
        video_format = content_type.split("/")[-1] if "/" in content_type else "mp4"

        # Store the video result
        # Note: The API doesn't return width/height/duration/fps, so we use defaults
        # The actual dimensions will be the same as the input video
        artifact = await context.store_video_result(
            storage_url=video_url,
            format=video_format,
            width=inputs.video.width,
            height=inputs.video.height,
            duration=inputs.audio.duration,
            fps=inputs.video.fps,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: SyncLipsyncV2Input) -> float:
        """Estimate cost for sync-lipsync v2 generation in USD.

        Pricing not specified in documentation, using estimate based on
        typical video processing costs. Pro model costs ~1.67x more.
        """
        # Base cost estimate per generation
        base_cost = 0.05

        # Pro model multiplier
        if inputs.model == "lipsync-2-pro":
            return base_cost * 1.67

        return base_cost
