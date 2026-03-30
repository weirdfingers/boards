"""
Kling v2.6 Pro image-to-video generator.

High-quality image-to-video generation with native audio synthesis
using Kling's v2.6 Pro model.

Based on Fal AI's fal-ai/kling-video/v2.6/pro/image-to-video model.
See: https://fal.ai/models/fal-ai/kling-video/v2.6/pro/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingVideoV26ProImageToVideoInput(BaseModel):
    """Input schema for Kling v2.6 Pro image-to-video generation.

    Artifact fields (image_url) are automatically detected via type introspection
    and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="Text description of desired video content",
        max_length=2500,
    )
    image_url: ImageArtifact = Field(
        description="Source image for animation",
    )
    duration: Literal["5", "10"] = Field(
        default="5",
        description="Video length in seconds",
    )
    negative_prompt: str = Field(
        default="blur, distort, and low quality",
        description="Elements to exclude from output",
        max_length=2500,
    )
    cfg_scale: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Guidance strength controlling prompt adherence (0-1)",
    )
    generate_audio: bool = Field(
        default=True,
        description="Enable native audio synthesis (supports Chinese and English)",
    )
    end_image_url: ImageArtifact | None = Field(
        default=None,
        description="Optional image for the video's ending frame",
    )


class FalKlingVideoV26ProImageToVideoGenerator(BaseGenerator):
    """Generator for image-to-video using Kling v2.6 Pro."""

    name = "fal-kling-video-v2-6-pro-image-to-video"
    description = "Fal: Kling v2.6 Pro - image-to-video generation with native audio synthesis"
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingVideoV26ProImageToVideoInput]:
        """Return the input schema for this generator."""
        return KlingVideoV26ProImageToVideoInput

    async def generate(
        self, inputs: KlingVideoV26ProImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Kling v2.6 Pro image-to-video model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingVideoV26ProImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact(s) to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        artifacts_to_upload = [inputs.image_url]
        if inputs.end_image_url is not None:
            artifacts_to_upload.append(inputs.end_image_url)

        image_urls = await upload_artifacts_to_fal(artifacts_to_upload, context)

        # Prepare arguments for fal.ai API
        # Note: v2.6 uses start_image_url instead of image_url
        arguments: dict = {
            "prompt": inputs.prompt,
            "start_image_url": image_urls[0],
            "duration": inputs.duration,
            "negative_prompt": inputs.negative_prompt,
            "cfg_scale": inputs.cfg_scale,
            "generate_audio": inputs.generate_audio,
        }

        if inputs.end_image_url is not None:
            arguments["end_image_url"] = image_urls[1]

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/v2.6/pro/image-to-video",
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

        # Determine video dimensions based on input image
        # Kling maintains the aspect ratio of the input image
        # Use input image dimensions as reference
        width = inputs.image_url.width
        height = inputs.image_url.height

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=float(inputs.duration),  # Convert "5" or "10" to float
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: KlingVideoV26ProImageToVideoInput) -> float:
        """Estimate cost for Kling v2.6 Pro image-to-video generation.

        Pricing per second:
        - Without audio: $0.07/sec
        - With audio: $0.14/sec
        """
        duration_seconds = float(inputs.duration)
        cost_per_second = 0.14 if inputs.generate_audio else 0.07
        return duration_seconds * cost_per_second
