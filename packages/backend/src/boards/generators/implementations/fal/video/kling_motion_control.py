"""
Kling Motion Control generator.

Transfer movements from a reference video to any character image. Cost-effective mode
for motion transfer, perfect for portraits and simple animations.

Based on Fal AI's fal-ai/kling-video/v2.6/standard/motion-control model.
See: https://fal.ai/models/fal-ai/kling-video/v2.6/standard/motion-control
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact, VideoArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingMotionControlInput(BaseModel):
    """Input schema for Kling Motion Control.

    Artifact fields (image_url, video_url) are automatically detected via type
    introspection and resolved from generation IDs to artifact objects.
    """

    image_url: ImageArtifact = Field(
        description="Reference image URL for character, background, and elements",
    )
    video_url: VideoArtifact = Field(
        description="Reference video URL for character motion consistency",
    )
    character_orientation: Literal["image", "video"] = Field(
        description=(
            "Character orientation mode. 'image' matches reference image orientation "
            "(better for camera movements, up to 10s). 'video' matches reference video "
            "orientation (better for complex motions, up to 30s)."
        ),
    )
    prompt: str | None = Field(
        default=None,
        description="Description of desired action (e.g., 'An african american woman dancing')",
        max_length=2500,
    )
    keep_original_sound: bool = Field(
        default=True,
        description="Preserve audio from reference video",
    )


class FalKlingMotionControlGenerator(BaseGenerator):
    """Generator for motion transfer using Kling v2.6 Standard Motion Control."""

    name = "fal-kling-motion-control"
    description = (
        "Fal: Kling Motion Control - transfer movements from a reference video "
        "to any character image"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingMotionControlInput]:
        """Return the input schema for this generator."""
        return KlingMotionControlInput

    async def generate(
        self, inputs: KlingMotionControlInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Kling v2.6 Standard Motion Control."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingMotionControlGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image and video artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        video_urls = await upload_artifacts_to_fal([inputs.video_url], context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "image_url": image_urls[0],
            "video_url": video_urls[0],
            "character_orientation": inputs.character_orientation,
            "keep_original_sound": inputs.keep_original_sound,
        }

        # Add optional prompt if provided
        if inputs.prompt is not None:
            arguments["prompt"] = inputs.prompt

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/v2.6/standard/motion-control",
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

        # Determine video dimensions based on character_orientation
        # In 'image' mode, output matches the reference image dimensions
        # In 'video' mode, output matches the reference video dimensions
        if inputs.character_orientation == "image":
            width = inputs.image_url.width
            height = inputs.image_url.height
        else:
            width = inputs.video_url.width
            height = inputs.video_url.height

        # Duration depends on mode and source:
        # 'image' mode: up to 10s
        # 'video' mode: up to 30s, based on source video duration
        # Use the source video duration as reference
        duration = inputs.video_url.duration if inputs.video_url.duration else 5.0

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=duration,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: KlingMotionControlInput) -> float:
        """Estimate cost for Kling Motion Control generation.

        Pricing information not provided in official documentation.
        Estimated at $0.12 per video based on typical Kling video generation costs.
        Cost may vary based on duration and orientation mode.
        """
        # Base cost per video
        # Longer videos ('video' mode supports up to 30s) may cost more
        base_cost = 0.12

        # Apply multiplier based on orientation mode
        # 'video' mode supports longer videos (up to 30s) so costs more
        if inputs.character_orientation == "video":
            return base_cost * 2.0  # Up to 30s
        else:
            return base_cost  # Up to 10s
