"""
Sora 2 Pro text-to-video generator.

OpenAI's state-of-the-art video model capable of creating richly detailed,
dynamic clips with audio from natural language descriptions.

Based on Fal AI's fal-ai/sora-2/text-to-video/pro model.
See: https://fal.ai/models/fal-ai/sora-2/text-to-video/pro
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Sora2TextToVideoProInput(BaseModel):
    """Input schema for Sora 2 Pro text-to-video generation."""

    prompt: str = Field(
        description="Describes the desired video",
        min_length=1,
        max_length=5000,
    )
    resolution: Literal["720p", "1080p"] = Field(
        default="1080p",
        description="Video resolution",
    )
    aspect_ratio: Literal["9:16", "16:9"] = Field(
        default="16:9",
        description="Video aspect ratio",
    )
    duration: Literal[4, 8, 12] = Field(
        default=4,
        description="Video duration in seconds",
    )


class FalSora2TextToVideoProGenerator(BaseGenerator):
    """Generator for text-to-video using Sora 2 Pro."""

    name = "fal-sora-2-text-to-video-pro"
    description = "Fal: Sora 2 Pro - OpenAI's state-of-the-art text-to-video model with audio"
    artifact_type = "video"

    def get_input_schema(self) -> type[Sora2TextToVideoProInput]:
        """Return the input schema for this generator."""
        return Sora2TextToVideoProInput

    async def generate(
        self, inputs: Sora2TextToVideoProInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Sora 2 Pro model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalSora2TextToVideoProGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "resolution": inputs.resolution,
            "aspect_ratio": inputs.aspect_ratio,
            "duration": inputs.duration,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/sora-2/text-to-video/pro",
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
        # fal.ai returns: {"video": {"url": "...", "width": 1920, "height": 1080, ...}}
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract dimensions from response
        width = video_data.get("width", 1920)
        height = video_data.get("height", 1080)
        fps = video_data.get("fps")
        duration = video_data.get("duration", float(inputs.duration))

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=duration,
            fps=fps,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: Sora2TextToVideoProInput) -> float:
        """Estimate cost for Sora 2 Pro generation.

        Pricing information not available in official documentation.
        Estimated at $0.20-$0.80 per video based on duration and resolution.
        Actual costs may vary.
        """
        # Base cost per second of video
        # Higher resolution and longer duration increase cost
        base_cost_per_second = 0.05

        # Resolution multiplier
        resolution_multiplier = 1.5 if inputs.resolution == "1080p" else 1.0

        # Calculate total cost
        total_cost = base_cost_per_second * inputs.duration * resolution_multiplier

        return total_cost
