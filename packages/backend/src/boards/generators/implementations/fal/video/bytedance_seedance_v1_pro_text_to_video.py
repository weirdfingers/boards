"""
Bytedance Seedance 1.0 Pro text-to-video generator.

A high quality video generation model developed by Bytedance that transforms
text prompts into professional-grade videos with customizable parameters.

Based on Fal AI's fal-ai/bytedance/seedance/v1/pro/text-to-video model.
See: https://fal.ai/models/fal-ai/bytedance/seedance/v1/pro/text-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class BytedanceSeedanceV1ProTextToVideoInput(BaseModel):
    """Input schema for Bytedance Seedance 1.0 Pro text-to-video generation."""

    prompt: str = Field(
        description="Text description of the desired video content",
    )
    aspect_ratio: Literal["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"] = Field(
        default="16:9",
        description="Video aspect ratio",
    )
    resolution: Literal["480p", "720p", "1080p"] = Field(
        default="1080p",
        description="Video resolution quality",
    )
    duration: Literal["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"] = Field(
        default="5",
        description="Video length in seconds (2-12)",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter unsafe content",
    )
    camera_fixed: bool = Field(
        default=False,
        description="Whether to fix camera position during generation",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility; use -1 for randomization",
    )


class FalBytedanceSeedanceV1ProTextToVideoGenerator(BaseGenerator):
    """Generator for text-to-video using Bytedance Seedance 1.0 Pro."""

    name = "fal-bytedance-seedance-v1-pro-text-to-video"
    description = "Fal: Bytedance Seedance 1.0 Pro - high quality text-to-video generation"
    artifact_type = "video"

    def get_input_schema(self) -> type[BytedanceSeedanceV1ProTextToVideoInput]:
        """Return the input schema for this generator."""
        return BytedanceSeedanceV1ProTextToVideoInput

    async def generate(
        self, inputs: BytedanceSeedanceV1ProTextToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Bytedance Seedance 1.0 Pro model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBytedanceSeedanceV1ProTextToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "duration": inputs.duration,
            "enable_safety_checker": inputs.enable_safety_checker,
            "camera_fixed": inputs.camera_fixed,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/bytedance/seedance/v1/pro/text-to-video",
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
        # fal.ai returns: {"video": {"url": "...", "content_type": "video/mp4", ...}, "seed": 123}
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

    async def estimate_cost(self, inputs: BytedanceSeedanceV1ProTextToVideoInput) -> float:
        """Estimate cost for Bytedance Seedance 1.0 Pro generation.

        Pricing information not provided in official documentation.
        Estimated at $0.12 per video based on typical video generation costs.
        Cost may vary based on duration and resolution settings.
        """
        # Base cost per video
        base_cost = 0.12

        # Adjust for longer durations (higher cost for longer videos)
        duration_seconds = int(inputs.duration)
        duration_multiplier = 1.0 + ((duration_seconds - 5) * 0.05)  # +5% per second above 5s

        # Adjust for higher resolutions
        resolution_multiplier = {
            "480p": 0.8,  # Lower quality, lower cost
            "720p": 1.0,  # Standard
            "1080p": 1.3,  # Higher quality, higher cost
        }[inputs.resolution]

        return base_cost * duration_multiplier * resolution_multiplier
