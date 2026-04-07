"""
ByteDance SeedDance v1.5 Pro text-to-video generator.

A high quality video generation model developed by ByteDance that transforms
text prompts into professional-grade videos with native audio generation.

Based on Fal AI's fal-ai/bytedance/seedance/v1.5/pro/text-to-video model.
See: https://fal.ai/models/fal-ai/bytedance/seedance/v1.5/pro/text-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class BytedanceSeedanceV15ProTextToVideoInput(BaseModel):
    """Input schema for ByteDance SeedDance v1.5 Pro text-to-video generation."""

    prompt: str = Field(
        description="Text description of the desired video content",
    )
    aspect_ratio: Literal["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"] = Field(
        default="16:9",
        description="Video aspect ratio",
    )
    resolution: Literal["480p", "720p", "1080p"] = Field(
        default="720p",
        description="Video resolution quality",
    )
    duration: int = Field(
        default=5,
        ge=4,
        le=12,
        description="Video length in seconds (4-12)",
    )
    generate_audio: bool = Field(
        default=True,
        description="Enable native audio generation for the video",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter unsafe content",
    )
    camera_fixed: bool = Field(
        default=False,
        description="Lock camera position to prevent camera movement",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility; use -1 for randomization",
    )


class FalBytedanceSeedanceV15ProTextToVideoGenerator(BaseGenerator):
    """Generator for text-to-video using ByteDance SeedDance v1.5 Pro."""

    name = "fal-bytedance-seedance-v1-5-pro-text-to-video"
    description = (
        "Fal: SeedDance v1.5 Pro - High quality text-to-video generation with audio by ByteDance"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[BytedanceSeedanceV15ProTextToVideoInput]:
        """Return the input schema for this generator."""
        return BytedanceSeedanceV15ProTextToVideoInput

    async def generate(
        self, inputs: BytedanceSeedanceV15ProTextToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai bytedance/seedance/v1.5/pro/text-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBytedanceSeedanceV15ProTextToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "duration": inputs.duration,
            "generate_audio": inputs.generate_audio,
            "enable_safety_checker": inputs.enable_safety_checker,
            "camera_fixed": inputs.camera_fixed,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/bytedance/seedance/v1.5/pro/text-to-video",
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

        # Calculate video dimensions based on aspect ratio and resolution
        width, height = self._calculate_dimensions(inputs.aspect_ratio, inputs.resolution)

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

    def _calculate_dimensions(self, aspect_ratio: str, resolution: str) -> tuple[int, int]:
        """Calculate video dimensions based on aspect ratio and resolution.

        Args:
            aspect_ratio: Video aspect ratio (e.g., "16:9", "21:9")
            resolution: Video resolution (e.g., "1080p", "720p", "480p")

        Returns:
            Tuple of (width, height) in pixels
        """
        # Base heights for each resolution
        resolution_heights = {
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
        }

        # Parse aspect ratio
        aspect_parts = aspect_ratio.split(":")
        aspect_width = int(aspect_parts[0])
        aspect_height = int(aspect_parts[1])

        # Get base height for resolution
        height = resolution_heights[resolution]

        # Calculate width based on aspect ratio
        width = int((height * aspect_width) / aspect_height)

        return width, height

    async def estimate_cost(self, inputs: BytedanceSeedanceV15ProTextToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Based on fal.ai pricing for Seedance v1.5 Pro:
        - With audio: $2.4 per 1M video tokens
        - Without audio: $1.2 per 1M video tokens

        Formula: tokens(video) = (height x width x FPS x duration) / 1024
        """
        width, height = self._calculate_dimensions(inputs.aspect_ratio, inputs.resolution)

        # Assume 30 FPS for video generation
        fps = 30

        # Calculate video tokens
        tokens = (height * width * fps * inputs.duration) / 1024

        # Price per million tokens depends on audio
        price_per_million_tokens = 2.4 if inputs.generate_audio else 1.2

        # Calculate cost
        cost = (tokens / 1_000_000) * price_per_million_tokens

        return cost
