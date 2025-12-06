"""
Wan 2.5 Preview text-to-video generator.

A text-to-video generation model that converts text prompts into video content,
supporting both Chinese and English inputs up to 800 characters.

Based on Fal AI's fal-ai/wan-25-preview/text-to-video model.
See: https://fal.ai/models/fal-ai/wan-25-preview/text-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Wan25PreviewTextToVideoInput(BaseModel):
    """Input schema for Wan 2.5 Preview text-to-video generation.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="Text prompt for video generation. Supports Chinese and English.",
        min_length=1,
        max_length=800,
    )
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    resolution: Literal["480p", "720p", "1080p"] = Field(
        default="1080p",
        description="Resolution of the generated video",
    )
    duration: Literal[5, 10] = Field(
        default=5,
        description="Duration of the generated video in seconds",
    )
    audio_url: str | None = Field(
        default=None,
        description="URL of background audio (WAV/MP3). Must be 3-30 seconds and max 15MB. "
        "Audio longer than video is truncated; shorter audio results in silent sections.",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Whether to enable safety filtering",
    )
    negative_prompt: str | None = Field(
        default=None,
        description="Content to avoid in generation",
        max_length=500,
    )
    enable_prompt_expansion: bool = Field(
        default=True,
        description="Whether to expand short prompts for improved results. "
        "Increases processing time but improves quality for short prompts.",
    )


class FalWan25PreviewTextToVideoGenerator(BaseGenerator):
    """Generator for text-to-video using Wan 2.5 Preview."""

    name = "fal-wan-25-preview-text-to-video"
    description = (
        "Fal: Wan 2.5 Preview - Text-to-video generation supporting "
        "Chinese/English prompts up to 800 characters"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[Wan25PreviewTextToVideoInput]:
        """Return the input schema for this generator."""
        return Wan25PreviewTextToVideoInput

    async def generate(
        self, inputs: Wan25PreviewTextToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Wan 2.5 Preview model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalWan25PreviewTextToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "duration": inputs.duration,
            "enable_safety_checker": inputs.enable_safety_checker,
            "enable_prompt_expansion": inputs.enable_prompt_expansion,
        }

        # Add optional parameters
        if inputs.audio_url is not None:
            arguments["audio_url"] = inputs.audio_url
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed
        if inputs.negative_prompt is not None:
            arguments["negative_prompt"] = inputs.negative_prompt

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/wan-25-preview/text-to-video",
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
            resolution_dimensions = {
                "480p": {"16:9": (854, 480), "9:16": (480, 854), "1:1": (480, 480)},
                "720p": {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (720, 720)},
                "1080p": {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)},
            }
            dims = resolution_dimensions.get(inputs.resolution, {}).get(
                inputs.aspect_ratio, (1920, 1080)
            )
            width, height = dims

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

    async def estimate_cost(self, inputs: Wan25PreviewTextToVideoInput) -> float:
        """Estimate cost for Wan 2.5 Preview generation.

        Pricing information not provided in official documentation.
        Estimated at $0.10 per 5-second video based on typical video generation costs.
        Cost scales with duration.
        """
        # Base cost per 5-second video
        base_cost = 0.10
        # Scale by duration: 5s = 1x, 10s = 2x
        duration_multiplier = inputs.duration / 5
        return base_cost * duration_multiplier
