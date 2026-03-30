"""
LTX-2.3 Pro text-to-video generator.

A high-quality, fast AI video model with audio support. Generates videos
from text prompts at up to 2160p resolution with configurable frame rates.

Based on Fal AI's fal-ai/ltx-2.3/text-to-video model.
See: https://fal.ai/models/fal-ai/ltx-2.3/text-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Ltx23TextToVideoInput(BaseModel):
    """Input schema for LTX-2.3 Pro text-to-video generation."""

    prompt: str = Field(
        description="Text prompt for video generation.",
        min_length=1,
        max_length=5000,
    )
    duration: Literal[6, 8, 10] = Field(
        default=6,
        description="Duration of the generated video in seconds",
    )
    resolution: Literal["1080p", "1440p", "2160p"] = Field(
        default="1080p",
        description="Resolution of the generated video",
    )
    aspect_ratio: Literal["16:9", "9:16"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    fps: Literal[24, 25, 48, 50] = Field(
        default=25,
        description="Frame rate of the generated video",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate audio for the video",
    )


class FalLtx23TextToVideoGenerator(BaseGenerator):
    """Generator for text-to-video using LTX-2.3 Pro."""

    name = "fal-ltx-23-text-to-video"
    description = (
        "Fal: LTX-2.3 Pro - High-quality text-to-video generation " "with audio support up to 2160p"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[Ltx23TextToVideoInput]:
        """Return the input schema for this generator."""
        return Ltx23TextToVideoInput

    async def generate(
        self, inputs: Ltx23TextToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai LTX-2.3 Pro model."""
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalLtx23TextToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        arguments: dict = {
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "resolution": inputs.resolution,
            "aspect_ratio": inputs.aspect_ratio,
            "fps": inputs.fps,
            "generate_audio": inputs.generate_audio,
        }

        handler = await fal_client.submit_async(
            "fal-ai/ltx-2.3/text-to-video",
            arguments=arguments,
        )

        await context.set_external_job_id(handler.request_id)

        from .....progress.models import ProgressUpdate

        event_count = 0
        async for event in handler.iter_events(with_logs=True):
            event_count += 1
            if event_count % 3 == 0:
                logs = getattr(event, "logs", None)
                if logs:
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

        result = await handler.get()

        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Determine fallback dimensions based on resolution and aspect ratio
        resolution_dimensions = {
            "1080p": {"16:9": (1920, 1080), "9:16": (1080, 1920)},
            "1440p": {"16:9": (2560, 1440), "9:16": (1440, 2560)},
            "2160p": {"16:9": (3840, 2160), "9:16": (2160, 3840)},
        }
        default_width, default_height = resolution_dimensions.get(inputs.resolution, {}).get(
            inputs.aspect_ratio, (1920, 1080)
        )

        width = video_data.get("width", default_width)
        height = video_data.get("height", default_height)
        fps = video_data.get("fps", inputs.fps)
        duration = video_data.get("duration", inputs.duration)

        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=float(duration),
            fps=fps,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: Ltx23TextToVideoInput) -> float:
        """Estimate cost for LTX-2.3 Pro generation.

        Estimated at $0.12 per 6-second video. Cost scales with duration.
        """
        base_cost = 0.12
        duration_multiplier = inputs.duration / 6
        return base_cost * duration_multiplier
