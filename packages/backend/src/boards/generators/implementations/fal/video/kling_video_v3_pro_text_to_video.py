"""
Kling 3.0 Pro text-to-video generator.

Top-tier text-to-video generation with cinematic visuals, fluid motion,
native audio generation, and multi-shot support using Kling's v3 Pro model.

Based on Fal AI's fal-ai/kling-video/v3/pro/text-to-video model.
See: https://fal.ai/models/fal-ai/kling-video/v3/pro/text-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingVideoV3ProTextToVideoInput(BaseModel):
    """Input schema for Kling 3.0 Pro text-to-video generation."""

    prompt: str = Field(
        description="Primary instruction for video generation",
        max_length=2500,
    )
    duration: Literal["5", "10"] = Field(
        default="5",
        description="Video length in seconds",
    )
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = Field(
        default="16:9",
        description="Frame dimensions",
    )
    negative_prompt: str = Field(
        default="blur, distort, and low quality",
        description="Elements to exclude from output",
        max_length=2500,
    )
    cfg_scale: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Guidance strength controlling prompt adherence (0-1)",
    )
    generate_audio: bool = Field(
        default=True,
        description="Generate native audio with the video",
    )


class FalKlingVideoV3ProTextToVideoGenerator(BaseGenerator):
    """Generator for text-to-video using Kling 3.0 Pro."""

    name = "fal-kling-video-v3-pro-text-to-video"
    description = (
        "Fal: Kling 3.0 Pro - top-tier text-to-video with cinematic visuals and native audio"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingVideoV3ProTextToVideoInput]:
        """Return the input schema for this generator."""
        return KlingVideoV3ProTextToVideoInput

    async def generate(
        self, inputs: KlingVideoV3ProTextToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai Kling 3.0 Pro model."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingVideoV3ProTextToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "aspect_ratio": inputs.aspect_ratio,
            "negative_prompt": inputs.negative_prompt,
            "cfg_scale": inputs.cfg_scale,
            "generate_audio": inputs.generate_audio,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/v3/pro/text-to-video",
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

        # Determine video dimensions based on aspect ratio
        # Using HD quality resolutions
        aspect_ratio_dimensions = {
            "16:9": (1920, 1080),
            "9:16": (1080, 1920),
            "1:1": (1080, 1080),
        }
        width, height = aspect_ratio_dimensions.get(inputs.aspect_ratio, (1920, 1080))

        # Store video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=float(inputs.duration),  # Convert "5" or "10" to float
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: KlingVideoV3ProTextToVideoInput) -> float:
        """Estimate cost for Kling 3.0 Pro generation.

        Pricing: $0.112/sec (no audio), $0.168/sec (with audio).
        """
        per_second = 0.168 if inputs.generate_audio else 0.112
        return per_second * int(inputs.duration)
