"""
MiniMax Hailuo 02 [Standard] text-to-video generator.

Advanced video generation model with 768p resolution that converts text prompts
into video content. Supports 6 and 10 second durations with optional prompt optimization.

Based on Fal AI's fal-ai/minimax/hailuo-02/standard/text-to-video model.
See: https://fal.ai/models/fal-ai/minimax/hailuo-02/standard/text-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class FalMinimaxHailuo02StandardTextToVideoInput(BaseModel):
    """Input schema for MiniMax Hailuo 02 Standard text-to-video generation."""

    prompt: str = Field(
        description="Text description of the video to generate",
        min_length=1,
        max_length=2000,
    )
    duration: Literal["6", "10"] = Field(
        default="6",
        description="Video duration in seconds. Choose 6 or 10 seconds.",
    )
    prompt_optimizer: bool = Field(
        default=True,
        description="Enable the model's prompt optimization to enhance generation quality",
    )


class FalMinimaxHailuo02StandardTextToVideoGenerator(BaseGenerator):
    """Generator for text-to-video using MiniMax Hailuo 02 Standard model."""

    name = "fal-minimax-hailuo-02-standard-text-to-video"
    description = "Fal: MiniMax Hailuo 02 [Standard] - Advanced 768p text-to-video generation"
    artifact_type = "video"

    def get_input_schema(self) -> type[FalMinimaxHailuo02StandardTextToVideoInput]:
        """Return the input schema for this generator."""
        return FalMinimaxHailuo02StandardTextToVideoInput

    async def generate(
        self,
        inputs: FalMinimaxHailuo02StandardTextToVideoInput,
        context: GeneratorExecutionContext,
    ) -> GeneratorResult:
        """Generate video using fal.ai MiniMax Hailuo 02 Standard model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalMinimaxHailuo02StandardTextToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "prompt_optimizer": inputs.prompt_optimizer,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/minimax/hailuo-02/standard/text-to-video",
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

        # Hailuo 02 Standard produces 768p resolution videos
        # Using standard 16:9 aspect ratio dimensions for 768p
        width = 1360
        height = 768

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=float(inputs.duration),  # Convert "6" or "10" to float
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: FalMinimaxHailuo02StandardTextToVideoInput) -> float:
        """Estimate cost for MiniMax Hailuo 02 Standard generation.

        Pricing information not provided in official documentation.
        Estimated at $0.12 per video based on typical video generation costs.
        Cost may vary based on duration settings.
        """
        # Approximate cost per video
        # 10-second videos may cost more than 6-second videos
        base_cost = 0.12
        duration_multiplier = 1.67 if inputs.duration == "10" else 1.0
        return base_cost * duration_multiplier
