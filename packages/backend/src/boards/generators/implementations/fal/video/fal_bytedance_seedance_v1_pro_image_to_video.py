"""
ByteDance SeedDance v1 Pro image-to-video generator.

A high quality video generation model developed by ByteDance that converts static
images into dynamic videos based on textual descriptions.

Based on Fal AI's fal-ai/bytedance/seedance/v1/pro/image-to-video model.
See: https://fal.ai/models/fal-ai/bytedance/seedance/v1/pro/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class BytedanceSeedanceV1ProImageToVideoInput(BaseModel):
    """Input schema for ByteDance SeedDance v1 Pro image-to-video generation.

    Artifact fields (image, end_image) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(description="Text description for video generation")
    image: ImageArtifact = Field(description="Source image for conversion to video")
    aspect_ratio: Literal["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "auto"] = Field(
        default="auto",
        description=(
            "Aspect ratio of the generated video. 'auto' uses the aspect ratio from input image"
        ),
    )
    resolution: Literal["480p", "720p", "1080p"] = Field(
        default="1080p",
        description="Resolution of the generated video",
    )
    duration: Literal["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"] = Field(
        default="5",
        description="Duration of the generated video in seconds",
    )
    end_image: ImageArtifact | None = Field(
        default=None,
        description="Optional ending frame image for directional guidance",
    )
    camera_fixed: bool = Field(
        default=False,
        description="Lock camera position to prevent camera movement",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible results. Use -1 for random seed",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Activate content filtering to ensure safe outputs",
    )


class FalBytedanceSeedanceV1ProImageToVideoGenerator(BaseGenerator):
    """Generator for converting images to videos using ByteDance SeedDance v1 Pro."""

    name = "fal-bytedance-seedance-v1-pro-image-to-video"
    description = "Fal: SeedDance v1 Pro - High quality image-to-video generation by ByteDance"
    artifact_type = "video"

    def get_input_schema(self) -> type[BytedanceSeedanceV1ProImageToVideoInput]:
        """Return the input schema for this generator."""
        return BytedanceSeedanceV1ProImageToVideoInput

    async def generate(
        self, inputs: BytedanceSeedanceV1ProImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai bytedance/seedance/v1/pro/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBytedanceSeedanceV1ProImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": image_urls[0],
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "duration": inputs.duration,
            "camera_fixed": inputs.camera_fixed,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Upload end image if provided
        if inputs.end_image is not None:
            end_image_urls = await upload_artifacts_to_fal([inputs.end_image], context)
            arguments["end_image_url"] = end_image_urls[0]

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/bytedance/seedance/v1/pro/image-to-video",
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
        # Expected structure: {"video": {"url": "...", "content_type": "...", ...}, "seed": 123}
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Determine video dimensions based on resolution
        # Resolution mapping based on standard video dimensions
        resolution_map = {
            "480p": (854, 480),
            "720p": (1280, 720),
            "1080p": (1920, 1080),
        }
        width, height = resolution_map.get(inputs.resolution, (1920, 1080))

        # Parse duration from string format
        duration_seconds = int(inputs.duration)

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=duration_seconds,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: BytedanceSeedanceV1ProImageToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Based on fal.ai pricing: approximately $0.74 per 1080p 5-second video.
        Cost scales based on resolution and duration.

        Formula: tokens(video) = (height x width x FPS x duration) / 1024
        Pricing: $3.0 per 1 million video tokens for image-to-video
        """
        # Resolution mapping
        resolution_map = {
            "480p": (854, 480),
            "720p": (1280, 720),
            "1080p": (1920, 1080),
        }
        width, height = resolution_map.get(inputs.resolution, (1920, 1080))

        # Parse duration
        duration_seconds = int(inputs.duration)

        # Assume 30 FPS for video generation
        fps = 30

        # Calculate video tokens
        # Formula from fal.ai: tokens = (height * width * fps * duration) / 1024
        tokens = (height * width * fps * duration_seconds) / 1024

        # Price per million tokens for image-to-video
        price_per_million_tokens = 3.0

        # Calculate cost
        cost = (tokens / 1_000_000) * price_per_million_tokens

        return cost
