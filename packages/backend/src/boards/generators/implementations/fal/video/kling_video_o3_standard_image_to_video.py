"""
Kling O3 Standard image-to-video generator.

Generates video from start and end frame images with text-driven style guidance
using Kling's O3 Standard model via fal.ai.

Based on Fal AI's fal-ai/kling-video/o3/standard/image-to-video model.
See: https://fal.ai/models/fal-ai/kling-video/o3/standard/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingVideoO3StandardImageToVideoInput(BaseModel):
    """Input schema for Kling O3 Standard image-to-video generation.

    Artifact fields (start_frame, end_frame) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="Text description of desired video content and style guidance",
        max_length=2500,
    )
    start_frame: ImageArtifact = Field(
        description="Start frame image for the video",
    )
    end_frame: ImageArtifact | None = Field(
        default=None,
        description="End frame image for the video (optional)",
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


class FalKlingVideoO3StandardImageToVideoGenerator(BaseGenerator):
    """Generator for image-to-video using Kling O3 Standard."""

    name = "fal-kling-video-o3-standard-image-to-video"
    description = (
        "Fal: Kling O3 Standard - image-to-video generation with start/end frame and style guidance"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingVideoO3StandardImageToVideoInput]:
        """Return the input schema for this generator."""
        return KlingVideoO3StandardImageToVideoInput

    async def generate(
        self, inputs: KlingVideoO3StandardImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Kling O3 Standard image-to-video model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingVideoO3StandardImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        artifacts_to_upload = [inputs.start_frame]
        if inputs.end_frame is not None:
            artifacts_to_upload.append(inputs.end_frame)

        uploaded_urls = await upload_artifacts_to_fal(artifacts_to_upload, context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "image_url": uploaded_urls[0],
            "duration": inputs.duration,
            "negative_prompt": inputs.negative_prompt,
            "cfg_scale": inputs.cfg_scale,
        }

        if inputs.end_frame is not None:
            arguments["tail_image_url"] = uploaded_urls[1]

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/o3/standard/image-to-video",
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
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Use start frame dimensions as reference
        width = inputs.start_frame.width
        height = inputs.start_frame.height

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=float(inputs.duration),
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: KlingVideoO3StandardImageToVideoInput) -> float:
        """Estimate cost for Kling O3 Standard image-to-video generation.

        Pricing information not provided in official documentation.
        Estimated at $0.10 per video based on typical standard-tier costs.
        Cost may vary based on duration.
        """
        base_cost = 0.10
        duration_multiplier = 2.0 if inputs.duration == "10" else 1.0
        return base_cost * duration_multiplier
