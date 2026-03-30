"""
xAI Grok Imagine Video reference-to-video generator.

Generates videos from multiple reference images using text prompts.
Uses @Image1, @Image2, etc. placeholders in prompts to reference specific images.

Based on Fal AI's xai/grok-imagine-video/reference-to-video model.
See: https://fal.ai/models/xai/grok-imagine-video/reference-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class GrokImagineVideoReferenceToVideoInput(BaseModel):
    """Input schema for Grok Imagine Video reference-to-video generation.

    Artifact fields (reference_images) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        max_length=4096,
        description=(
            "Text prompt describing the video to generate. "
            "Use @Image1, @Image2, etc. to reference specific images "
            "from reference_images in order."
        ),
    )
    reference_images: list[ImageArtifact] = Field(
        min_length=1,
        max_length=7,
        description=(
            "One or more reference images to guide video generation. "
            "Reference in prompt as @Image1, @Image2, etc. Maximum 7 images."
        ),
    )
    duration: int = Field(
        default=8,
        ge=1,
        le=10,
        description="Video duration in seconds (1-10)",
    )
    aspect_ratio: Literal["16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    resolution: Literal["480p", "720p"] = Field(
        default="480p",
        description="Resolution of the output video",
    )


class FalGrokImagineVideoReferenceToVideoGenerator(BaseGenerator):
    """Generator for creating videos from reference images using xAI Grok Imagine Video."""

    name = "fal-grok-imagine-video-reference-to-video"
    description = (
        "Fal: Grok Imagine Video - Generate videos from reference images with text prompts"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[GrokImagineVideoReferenceToVideoInput]:
        """Return the input schema for this generator."""
        return GrokImagineVideoReferenceToVideoInput

    async def generate(
        self, inputs: GrokImagineVideoReferenceToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai xai/grok-imagine-video/reference-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGrokImagineVideoReferenceToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        reference_image_urls = await upload_artifacts_to_fal(inputs.reference_images, context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "reference_image_urls": reference_image_urls,
            "duration": inputs.duration,
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "xai/grok-imagine-video/reference-to-video",
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
                logs = getattr(event, "logs", None)
                if logs:
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
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Determine dimensions from resolution and aspect ratio
        width, height = _resolve_dimensions(inputs.resolution, inputs.aspect_ratio)

        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=inputs.duration,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: GrokImagineVideoReferenceToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Based on Fal pricing: ~$0.05/second for video output.
        """
        return 0.05 * inputs.duration


def _resolve_dimensions(resolution: str, aspect_ratio: str) -> tuple[int, int]:
    """Resolve width and height from resolution and aspect ratio."""
    aspect_ratios = {
        "16:9": (16, 9),
        "4:3": (4, 3),
        "3:2": (3, 2),
        "1:1": (1, 1),
        "2:3": (2, 3),
        "3:4": (3, 4),
        "9:16": (9, 16),
    }

    ar_w, ar_h = aspect_ratios.get(aspect_ratio, (16, 9))

    if resolution == "720p":
        if ar_w >= ar_h:
            height = 720
            width = int(height * ar_w / ar_h)
        else:
            width = 720
            height = int(width * ar_h / ar_w)
    else:  # 480p
        if ar_w >= ar_h:
            height = 480
            width = int(height * ar_w / ar_h)
        else:
            width = 480
            height = int(width * ar_h / ar_w)

    return width, height
