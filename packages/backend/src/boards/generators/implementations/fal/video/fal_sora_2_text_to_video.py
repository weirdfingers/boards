"""
Sora 2 text-to-video generator.

Text-to-video endpoint for Sora 2, OpenAI's state-of-the-art video model capable of
creating richly detailed, dynamic clips with audio from natural language prompts.

Based on Fal AI's fal-ai/sora-2/text-to-video model.
See: https://fal.ai/models/fal-ai/sora-2/text-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Sora2TextToVideoInput(BaseModel):
    """Input schema for Sora 2 text-to-video generation.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="Text description of desired video",
        min_length=1,
        max_length=5000,
    )
    resolution: Literal["720p"] = Field(
        default="720p",
        description="Video output quality (currently only 720p is supported)",
    )
    aspect_ratio: Literal["9:16", "16:9"] = Field(
        default="16:9",
        description="Video dimensions",
    )
    duration: Literal[4, 8, 12] = Field(
        default=4,
        description="Video length in seconds",
    )


class FalSora2TextToVideoGenerator(BaseGenerator):
    """Generator for text-to-video using Sora 2."""

    name = "fal-sora-2-text-to-video"
    description = (
        "Fal: Sora 2 - OpenAI's state-of-the-art text-to-video with richly detailed, dynamic clips"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[Sora2TextToVideoInput]:
        """Return the input schema for this generator."""
        return Sora2TextToVideoInput

    async def generate(
        self, inputs: Sora2TextToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Sora 2 model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalSora2TextToVideoGenerator. "
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
            "fal-ai/sora-2/text-to-video",
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
        # fal.ai returns: {"video": {"url": "...", "content_type": "video/mp4",
        # "width": ..., "height": ..., "duration": ..., "fps": ...}}
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract video metadata from response or use defaults
        width = video_data.get("width")
        height = video_data.get("height")
        duration = video_data.get("duration")
        fps = video_data.get("fps")

        # If dimensions not provided, determine based on aspect ratio and resolution
        if width is None or height is None:
            # 720p dimensions
            aspect_ratio_dimensions = {
                "16:9": (1280, 720),
                "9:16": (720, 1280),
            }
            width, height = aspect_ratio_dimensions.get(inputs.aspect_ratio, (1280, 720))

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=float(duration) if duration else float(inputs.duration),
            fps=fps,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: Sora2TextToVideoInput) -> float:
        """Estimate cost for Sora 2 generation.

        Pricing information not provided in official documentation.
        Estimated at $0.20 per video based on typical high-quality video generation costs.
        Cost scales with duration.
        """
        # Approximate cost per video - Sora 2 is likely higher cost due to quality
        base_cost = 0.20
        # Scale by duration: 4s = 1x, 8s = 2x, 12s = 3x
        duration_multiplier = inputs.duration / 4
        return base_cost * duration_multiplier
