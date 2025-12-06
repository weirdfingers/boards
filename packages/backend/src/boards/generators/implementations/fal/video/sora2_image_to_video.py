"""
Sora 2 image-to-video generator.

OpenAI's state-of-the-art video generation model that creates richly detailed,
dynamic clips with audio from natural language prompts and images.

Based on Fal AI's fal-ai/sora-2/image-to-video model.
See: https://fal.ai/models/fal-ai/sora-2/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Sora2ImageToVideoInput(BaseModel):
    """Input schema for Sora 2 image-to-video generation.

    Artifact fields (image_url) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="The text prompt describing the video you want to generate",
        min_length=1,
        max_length=5000,
    )
    image_url: ImageArtifact = Field(description="The image to use as the first frame")
    resolution: Literal["auto", "720p"] = Field(
        default="auto",
        description="Resolution of the generated video",
    )
    aspect_ratio: Literal["auto", "9:16", "16:9"] = Field(
        default="auto",
        description="Aspect ratio of the generated video",
    )
    duration: Literal[4, 8, 12] = Field(
        default=4,
        description="Duration of the generated video in seconds",
    )


class FalSora2ImageToVideoGenerator(BaseGenerator):
    """Generator for creating videos from images using OpenAI's Sora 2."""

    name = "fal-sora2-image-to-video"
    description = "Fal: Sora 2 - Generate videos from images with audio"
    artifact_type = "video"

    def get_input_schema(self) -> type[Sora2ImageToVideoInput]:
        """Return the input schema for this generator."""
        return Sora2ImageToVideoInput

    async def generate(
        self, inputs: Sora2ImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai sora-2/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalSora2ImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": image_urls[0],
            "resolution": inputs.resolution,
            "aspect_ratio": inputs.aspect_ratio,
            "duration": inputs.duration,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/sora-2/image-to-video",
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
        # Expected structure: {"video": {"url": "...", "width": 1280, "height": 720, ...}}
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract metadata from response (if available)
        width = video_data.get("width", 1280)
        height = video_data.get("height", 720)
        duration_seconds = video_data.get("duration", inputs.duration)
        fps = video_data.get("fps", 30)

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=duration_seconds,
            fps=fps,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: Sora2ImageToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Note: Pricing information not disclosed in Fal documentation.
        Using placeholder value that should be updated with actual pricing.
        """
        # TODO: Update with actual pricing from Fal when available
        # Estimate based on duration - longer videos likely cost more
        base_cost = 0.20  # Placeholder estimate for 4s
        duration_multiplier = inputs.duration / 4.0
        return base_cost * duration_multiplier
