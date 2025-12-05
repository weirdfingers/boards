"""
fal.ai creatify/lipsync video generator.

Generates realistic lip-synchronization videos from audio and video inputs
using Creatify's lipsync model on fal.ai. Optimized for speed, quality, and
consistency.

Based on Fal AI's creatify/lipsync model.
See: https://fal.ai/models/creatify/lipsync
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, VideoArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class CreatifyLipsyncInput(BaseModel):
    """Input schema for creatify/lipsync.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    video: VideoArtifact = Field(description="The video to use for lipsync")
    audio: AudioArtifact = Field(description="The audio to use for lipsync")
    loop: bool = Field(
        default=True,
        description="Repeats video if shorter than audio",
    )


class FalCreatifyLipsyncGenerator(BaseGenerator):
    """Generator for realistic lip-synchronization videos."""

    name = "fal-creatify-lipsync"
    description = "Fal: Creatify Lipsync - Realistic lipsync video optimized for speed and quality"
    artifact_type = "video"

    def get_input_schema(self) -> type[CreatifyLipsyncInput]:
        """Return the input schema for this generator."""
        return CreatifyLipsyncInput

    async def generate(
        self, inputs: CreatifyLipsyncInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate lip-synced video using creatify/lipsync."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalCreatifyLipsyncGenerator. "
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
            "loop": inputs.loop,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "creatify/lipsync",
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
        # Creatify lipsync always produces MP4 videos, so default to mp4
        content_type = video_data.get("content_type", "video/mp4")
        if content_type.startswith("video/"):
            video_format = content_type.split("/")[-1]
        else:
            # If content_type is not a video mime type (e.g., application/octet-stream),
            # default to mp4 since creatify/lipsync only produces mp4 videos
            video_format = "mp4"

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

    async def estimate_cost(self, inputs: CreatifyLipsyncInput) -> float:
        """Estimate cost for creatify/lipsync generation in USD.

        Pricing not specified in documentation, using estimate based on
        typical video processing costs.
        """
        # Base cost estimate per generation
        return 0.05
