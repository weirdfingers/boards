"""
Google Veo 3.1 first-last frame to video generator.

Generates videos by interpolating between first and last frame images using
Google's Veo 3.1 technology via fal.ai.

Based on Fal AI's fal-ai/veo3.1/first-last-frame-to-video model.
See: https://fal.ai/models/fal-ai/veo3.1/first-last-frame-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Veo31FirstLastFrameToVideoInput(BaseModel):
    """Input schema for Veo 3.1 first-last frame to video generation.

    Artifact fields (first_frame, last_frame) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    first_frame: ImageArtifact = Field(description="The first frame of the video (input image)")
    last_frame: ImageArtifact = Field(description="The last frame of the video (input image)")
    prompt: str = Field(description="Text prompt describing the desired video content and motion")
    duration: Literal["8s"] = Field(
        default="8s",
        description="Duration of the generated video in seconds (currently only 8s is supported)",
    )
    aspect_ratio: Literal["auto", "9:16", "16:9", "1:1"] = Field(
        default="auto",
        description=(
            "Aspect ratio of the generated video. " "'auto' uses the aspect ratio from input images"
        ),
    )
    resolution: Literal["720p", "1080p"] = Field(
        default="720p",
        description="Resolution of the generated video",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate audio for the video. Disabling uses 50% fewer credits",
    )


class FalVeo31FirstLastFrameToVideoGenerator(BaseGenerator):
    """Generator for creating videos from first and last frame images using Google Veo 3.1."""

    name = "fal-veo31-first-last-frame-to-video"
    description = "Fal: Veo 3.1 - Generate videos by interpolating between first and last frames"
    artifact_type = "video"

    def get_input_schema(self) -> type[Veo31FirstLastFrameToVideoInput]:
        """Return the input schema for this generator."""
        return Veo31FirstLastFrameToVideoInput

    async def generate(
        self, inputs: Veo31FirstLastFrameToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai veo3.1/first-last-frame-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalVeo31FirstLastFrameToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        first_frame_urls = await upload_artifacts_to_fal([inputs.first_frame], context)
        last_frame_urls = await upload_artifacts_to_fal([inputs.last_frame], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "first_frame_url": first_frame_urls[0],
            "last_frame_url": last_frame_urls[0],
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "generate_audio": inputs.generate_audio,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/veo3.1/first-last-frame-to-video",
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
                                progress=50.0,
                                phase="processing",
                                message=message,
                            )
                        )

        # Get final result
        result = await handler.get()

        # Extract video from result
        # Expected structure: {"video": {"url": "...", "content_type": "...", ...}}
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Store video result
        # Note: Fal API doesn't provide video dimensions/duration in the response,
        # so we'll use defaults based on input parameters
        width = 1280 if inputs.resolution == "720p" else 1920
        height = 720 if inputs.resolution == "720p" else 1080

        # Parse duration from "8s" format
        duration_seconds = int(inputs.duration.rstrip("s"))

        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=duration_seconds,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: Veo31FirstLastFrameToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Note: Pricing information not available in Fal documentation.
        Using placeholder value that should be updated with actual pricing.
        """
        # TODO: Update with actual pricing from Fal when available
        # Base cost, with 50% reduction if audio is disabled
        base_cost = 0.15  # Placeholder estimate
        if not inputs.generate_audio:
            return base_cost * 0.5
        return base_cost
