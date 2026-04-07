"""
ByteDance SeedDance v1.5 Pro image-to-video generator.

A high quality video generation model developed by ByteDance that converts static
images into dynamic videos based on textual descriptions, with native audio generation.

Based on Fal AI's fal-ai/bytedance/seedance/v1.5/pro/image-to-video model.
See: https://fal.ai/models/fal-ai/bytedance/seedance/v1.5/pro/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class BytedanceSeedanceV15ProImageToVideoInput(BaseModel):
    """Input schema for ByteDance SeedDance v1.5 Pro image-to-video generation.

    Artifact fields (image, end_image) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(description="Text description for video generation")
    image: ImageArtifact = Field(description="Source image for conversion to video")
    aspect_ratio: Literal["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    resolution: Literal["480p", "720p"] = Field(
        default="720p",
        description="Resolution of the generated video",
    )
    duration: int = Field(
        default=5,
        ge=4,
        le=12,
        description="Duration of the generated video in seconds (4-12)",
    )
    end_image: ImageArtifact | None = Field(
        default=None,
        description="Optional ending frame image for directional guidance",
    )
    generate_audio: bool = Field(
        default=True,
        description="Enable native audio generation for the video",
    )
    camera_fixed: bool = Field(
        default=False,
        description="Lock camera position to prevent camera movement",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible results. Use -1 for random seed",
    )


class FalBytedanceSeedanceV15ProImageToVideoGenerator(BaseGenerator):
    """Generator for converting images to videos using ByteDance SeedDance v1.5 Pro."""

    name = "fal-bytedance-seedance-v1-5-pro-image-to-video"
    description = (
        "Fal: SeedDance v1.5 Pro - High quality image-to-video generation with audio by ByteDance"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[BytedanceSeedanceV15ProImageToVideoInput]:
        """Return the input schema for this generator."""
        return BytedanceSeedanceV15ProImageToVideoInput

    async def generate(
        self, inputs: BytedanceSeedanceV15ProImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai bytedance/seedance/v1.5/pro/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBytedanceSeedanceV15ProImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image], context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "image_url": image_urls[0],
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "duration": inputs.duration,
            "generate_audio": inputs.generate_audio,
            "camera_fixed": inputs.camera_fixed,
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
            "fal-ai/bytedance/seedance/v1.5/pro/image-to-video",
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
        resolution_map = {
            "480p": (854, 480),
            "720p": (1280, 720),
        }
        width, height = resolution_map.get(inputs.resolution, (1280, 720))

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=inputs.duration,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: BytedanceSeedanceV15ProImageToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Based on fal.ai pricing for Seedance v1.5 Pro:
        - With audio: $2.4 per 1M video tokens
        - Without audio: $1.2 per 1M video tokens

        Formula: tokens(video) = (height x width x FPS x duration) / 1024
        """
        # Resolution mapping
        resolution_map = {
            "480p": (854, 480),
            "720p": (1280, 720),
        }
        width, height = resolution_map.get(inputs.resolution, (1280, 720))

        # Assume 30 FPS for video generation
        fps = 30

        # Calculate video tokens
        tokens = (height * width * fps * inputs.duration) / 1024

        # Price per million tokens depends on audio
        price_per_million_tokens = 2.4 if inputs.generate_audio else 1.2

        # Calculate cost
        cost = (tokens / 1_000_000) * price_per_million_tokens

        return cost
