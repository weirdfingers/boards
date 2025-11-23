"""
Google Veo 3.1 image-to-video generator.

Converts static images into animated videos based on text prompts using
Google's Veo 3.1 technology via fal.ai.

Based on Fal AI's fal-ai/veo3.1/image-to-video model.
See: https://fal.ai/models/fal-ai/veo3.1/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Veo31ImageToVideoInput(BaseModel):
    """Input schema for Veo 3.1 image-to-video generation.

    Artifact fields (image) are automatically detected via type introspection
    and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(description="Text prompt describing the desired video content and motion")
    image: ImageArtifact = Field(
        description="Input image to animate. Should be 720p or higher in 16:9 or 9:16 aspect ratio"
    )
    aspect_ratio: Literal["9:16", "16:9"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    duration: Literal["4s", "6s", "8s"] = Field(
        default="8s",
        description="Duration of the generated video in seconds",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate audio for the video. Disabling uses 50% fewer credits",
    )
    resolution: Literal["720p", "1080p"] = Field(
        default="720p",
        description="Resolution of the generated video",
    )


class FalVeo31ImageToVideoGenerator(BaseGenerator):
    """Generator for creating videos from static images using Google Veo 3.1."""

    name = "fal-veo31-image-to-video"
    description = "Fal: Veo 3.1 - Convert images to videos with text-guided animation"
    artifact_type = "video"

    def get_input_schema(self) -> type[Veo31ImageToVideoInput]:
        """Return the input schema for this generator."""
        return Veo31ImageToVideoInput

    async def generate(
        self, inputs: Veo31ImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai veo3.1/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalVeo31ImageToVideoGenerator. "
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
            "fal-ai/veo3.1/image-to-video",
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
        if inputs.resolution == "720p":
            if inputs.aspect_ratio == "16:9":
                width, height = 1280, 720
            else:  # 9:16
                width, height = 720, 1280
        else:  # 1080p
            if inputs.aspect_ratio == "16:9":
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

    async def estimate_cost(self, inputs: Veo31ImageToVideoInput) -> float:
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
