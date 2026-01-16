"""
Kling Video v2.6 Pro Motion Control generator.

Applies movements from a reference video to character images using Kling's v2.6 Pro
motion control model. Particularly suited for complex dance moves and gestures.

Based on Fal AI's fal-ai/kling-video/v2.6/pro/motion-control model.
See: https://fal.ai/models/fal-ai/kling-video/v2.6/pro/motion-control
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact, VideoArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingVideoV26ProMotionControlInput(BaseModel):
    """Input schema for Kling v2.6 Pro Motion Control generation.

    Artifact fields (image_url, video_url) are automatically detected via type
    introspection and resolved from generation IDs to artifact objects.
    """

    image_url: ImageArtifact = Field(
        description="Reference image with character. "
        "Characters should have clear body proportions, avoid occlusion, "
        "and occupy more than 5% of the image area.",
    )
    video_url: VideoArtifact = Field(
        description="Reference video with motion to apply. "
        "Should feature a realistic style character with entire body or upper body visible, "
        "including head, without obstruction.",
    )
    character_orientation: Literal["image", "video"] = Field(
        description="Character orientation mode. "
        "'image' matches reference image orientation (optimal for camera movements, max 10s). "
        "'video' matches reference video orientation (optimal for complex motions, max 30s).",
    )
    prompt: str | None = Field(
        default=None,
        description="Optional text description of the desired motion",
        max_length=2500,
    )
    keep_original_sound: bool = Field(
        default=True,
        description="Whether to preserve the original sound from the reference video",
    )


class FalKlingVideoV26ProMotionControlGenerator(BaseGenerator):
    """Generator for motion control video using Kling v2.6 Pro."""

    name = "fal-kling-video-v26-pro-motion-control"
    description = (
        "Fal: Kling v2.6 Pro Motion Control - apply reference video motions to character images"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingVideoV26ProMotionControlInput]:
        """Return the input schema for this generator."""
        return KlingVideoV26ProMotionControlInput

    async def generate(
        self, inputs: KlingVideoV26ProMotionControlInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Kling v2.6 Pro motion control model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingVideoV26ProMotionControlGenerator. "
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
        if inputs.prompt:
            arguments["prompt"] = inputs.prompt

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/v2.6/pro/motion-control",
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

        # Use input video dimensions and duration as reference
        # Motion control maintains similar dimensions to the reference video
        width = inputs.video_url.width
        height = inputs.video_url.height
        duration = inputs.video_url.duration

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

    async def estimate_cost(self, inputs: KlingVideoV26ProMotionControlInput) -> float:
        """Estimate cost for Kling v2.6 Pro motion control generation.

        Pricing information not provided in official documentation.
        Estimated at $0.15 per video based on typical Kling video generation costs.
        """
        return 0.15
