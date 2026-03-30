"""
Kling 3.0 Pro image-to-video generator.

Top-tier image-to-video generation with cinematic visuals, fluid motion,
native audio generation, and custom element support using Kling's v3 Pro model.

Based on Fal AI's fal-ai/kling-video/v3/pro/image-to-video model.
See: https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingVideoV3ProImageToVideoInput(BaseModel):
    """Input schema for Kling 3.0 Pro image-to-video generation.

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
        description="Generate native audio with the video",
    )


class FalKlingVideoV3ProImageToVideoGenerator(BaseGenerator):
    """Generator for image-to-video using Kling 3.0 Pro."""

    name = "fal-kling-video-v3-pro-image-to-video"
    description = (
        "Fal: Kling 3.0 Pro - top-tier image-to-video with cinematic visuals and native audio"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingVideoV3ProImageToVideoInput]:
        """Return the input schema for this generator."""
        return KlingVideoV3ProImageToVideoInput

    async def generate(
        self, inputs: KlingVideoV3ProImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Kling 3.0 Pro image-to-video model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingVideoV3ProImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "start_image_url": image_urls[0],
            "duration": inputs.duration,
            "negative_prompt": inputs.negative_prompt,
            "cfg_scale": inputs.cfg_scale,
            "generate_audio": inputs.generate_audio,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/v3/pro/image-to-video",
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

    async def estimate_cost(self, inputs: KlingVideoV3ProImageToVideoInput) -> float:
        """Estimate cost for Kling 3.0 Pro image-to-video generation.

        Pricing: $0.112/sec (no audio), $0.168/sec (with audio).
        """
        per_second = 0.168 if inputs.generate_audio else 0.112
        return per_second * int(inputs.duration)
