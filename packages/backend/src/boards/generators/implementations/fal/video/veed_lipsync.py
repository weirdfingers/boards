"""
VEED Lipsync video generator.

Generate realistic lipsync from any audio using VEED's latest model.
This generator synchronizes lip movements in video with provided audio.

Based on Fal AI's veed/lipsync model.
See: https://fal.ai/models/veed/lipsync
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, VideoArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class VeedLipsyncInput(BaseModel):
    """Input schema for VEED lipsync.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    video_url: VideoArtifact = Field(description="Video to apply lip-sync animation to")
    audio_url: AudioArtifact = Field(description="Audio to synchronize with the video")


class FalVeedLipsyncGenerator(BaseGenerator):
    """Generator for realistic lip-synchronization using VEED's model."""

    name = "veed-lipsync"
    description = "VEED: Lipsync - Generate realistic lipsync from any audio"
    artifact_type = "video"

    def get_input_schema(self) -> type[VeedLipsyncInput]:
        """Return the input schema for this generator."""
        return VeedLipsyncInput

    async def generate(
        self, inputs: VeedLipsyncInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate lip-synced video using VEED lipsync."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalVeedLipsyncGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload video and audio artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        # Upload video and audio separately
        video_urls = await upload_artifacts_to_fal([inputs.video_url], context)
        audio_urls = await upload_artifacts_to_fal([inputs.audio_url], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "video_url": video_urls[0],
            "audio_url": audio_urls[0],
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "veed/lipsync",
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
        # VEED API returns: {"video": {"url": "...", "content_type": "video/mp4", ...}}
        video_data = result.get("video")

        if not video_data:
            raise ValueError("No video returned from VEED API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in VEED response")

        # Extract format from content_type (e.g., "video/mp4" -> "mp4")
        content_type = video_data.get("content_type", "video/mp4")
        video_format = content_type.split("/")[-1] if "/" in content_type else "mp4"

        # Store the video result
        # Note: The API doesn't return width/height/duration/fps in documentation
        # Using input video dimensions and audio duration
        artifact = await context.store_video_result(
            storage_url=video_url,
            format=video_format,
            width=inputs.video_url.width,
            height=inputs.video_url.height,
            duration=inputs.audio_url.duration,
            fps=inputs.video_url.fps,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: VeedLipsyncInput) -> float:
        """Estimate cost for VEED lipsync generation in USD.

        Pricing not specified in documentation, using estimate based on
        typical video lipsync processing costs.
        """
        # Base cost estimate per generation
        return 0.05
