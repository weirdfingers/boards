"""
Google Veo 3.1 Fast image-to-video generator.

Converts static images into animated videos based on text prompts using
Google's Veo 3.1 Fast technology via fal.ai. This is a faster version
with per-second pricing.

Based on Fal AI's fal-ai/veo3.1/fast/image-to-video model.
See: https://fal.ai/models/fal-ai/veo3.1/fast/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Veo31FastImageToVideoInput(BaseModel):
    """Input schema for Veo 3.1 Fast image-to-video generation.

    Artifact fields (image) are automatically detected via type introspection
    and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(description="Text prompt describing the desired video content and motion")
    image: ImageArtifact = Field(
        description="Input image to animate. Should be 720p or higher in 16:9 or 9:16 aspect ratio"
    )
    aspect_ratio: Literal["auto", "9:16", "16:9"] = Field(
        default="auto",
        description="Aspect ratio of the generated video. "
        "'auto' automatically detects from input image",
    )
    duration: Literal["4s", "6s", "8s"] = Field(
        default="8s",
        description="Duration of the generated video in seconds",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate audio for the video. Disabling reduces cost by ~33%",
    )
    resolution: Literal["720p", "1080p"] = Field(
        default="720p",
        description="Resolution of the generated video",
    )


class FalVeo31FastImageToVideoGenerator(BaseGenerator):
    """Generator for creating videos from static images using Google Veo 3.1 Fast."""

    name = "fal-veo31-fast-image-to-video"
    description = "Fal: Veo 3.1 Fast - Convert images to videos with text-guided animation"
    artifact_type = "video"

    def get_input_schema(self) -> type[Veo31FastImageToVideoInput]:
        """Return the input schema for this generator."""
        return Veo31FastImageToVideoInput

    async def generate(
        self, inputs: Veo31FastImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai veo3.1/fast/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalVeo31FastImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": image_urls[0],
            "aspect_ratio": inputs.aspect_ratio,
            "duration": inputs.duration,
            "generate_audio": inputs.generate_audio,
            "resolution": inputs.resolution,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/veo3.1/fast/image-to-video",
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

        # Calculate video dimensions based on resolution and aspect ratio
        # For "auto" aspect ratio, assume 16:9 as the most common format
        effective_aspect_ratio = inputs.aspect_ratio if inputs.aspect_ratio != "auto" else "16:9"

        if inputs.resolution == "720p":
            if effective_aspect_ratio == "16:9":
                width, height = 1280, 720
            else:  # 9:16
                width, height = 720, 1280
        else:  # 1080p
            if effective_aspect_ratio == "16:9":
                width, height = 1920, 1080
            else:  # 9:16
                width, height = 1080, 1920

        # Parse duration from "Xs" format
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

    async def estimate_cost(self, inputs: Veo31FastImageToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Pricing: $0.10 per second (audio off) or $0.15 per second (audio on).
        """
        # Parse duration from "Xs" format
        duration_seconds = int(inputs.duration.rstrip("s"))

        # Per-second pricing
        if inputs.generate_audio:
            cost_per_second = 0.15
        else:
            cost_per_second = 0.10

        return duration_seconds * cost_per_second
