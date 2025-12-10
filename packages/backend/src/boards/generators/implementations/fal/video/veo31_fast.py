"""
Google Veo 3.1 Fast text-to-video generator.

A faster, more cost-effective variant of Google's Veo 3.1 video generation model,
capable of generating high-quality videos from text prompts with optional audio synthesis.

Based on Fal AI's fal-ai/veo3.1/fast model.
See: https://fal.ai/models/fal-ai/veo3.1/fast
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Veo31FastInput(BaseModel):
    """Input schema for Google Veo 3.1 Fast text-to-video generation."""

    prompt: str = Field(description="The text prompt describing the video you want to generate")
    aspect_ratio: Literal["9:16", "16:9"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    duration: Literal["4s", "6s", "8s"] = Field(
        default="8s",
        description="Duration of the generated video",
    )
    resolution: Literal["720p", "1080p"] = Field(
        default="720p",
        description="Resolution of the generated video",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate audio for the video. If false, 33% less credits used",
    )
    enhance_prompt: bool = Field(
        default=True,
        description="Whether to enhance video generation",
    )
    auto_fix: bool = Field(
        default=True,
        description="Automatically attempt to fix prompts that fail content policy",
    )
    seed: int | None = Field(
        default=None,
        description="Seed value for reproducible generation",
    )
    negative_prompt: str | None = Field(
        default=None,
        description="Guidance text to exclude from generation",
    )


class FalVeo31FastGenerator(BaseGenerator):
    """Generator for text-to-video using Google Veo 3.1 Fast."""

    name = "fal-veo31-fast"
    description = "Fal: Veo 3.1 Fast - Google's fast AI video generation model"
    artifact_type = "video"

    def get_input_schema(self) -> type[Veo31FastInput]:
        """Return the input schema for this generator."""
        return Veo31FastInput

    async def generate(
        self, inputs: Veo31FastInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai veo3.1/fast."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalVeo31FastGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "duration": inputs.duration,
            "resolution": inputs.resolution,
            "generate_audio": inputs.generate_audio,
            "enhance_prompt": inputs.enhance_prompt,
            "auto_fix": inputs.auto_fix,
        }

        # Add optional parameters if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed
        if inputs.negative_prompt is not None:
            arguments["negative_prompt"] = inputs.negative_prompt

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/veo3.1/fast",
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
        # Expected structure: {"video": {"url": "...", "content_type": "...", ...}}
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Determine video dimensions based on resolution and aspect ratio
        if inputs.resolution == "720p":
            if inputs.aspect_ratio == "16:9":
                width, height = 1280, 720
            else:  # 9:16
                width, height = 720, 1280
        else:  # 1080p
            if inputs.aspect_ratio == "16:9":
                width, height = 1920, 1080
            else:  # 9:16
                width, height = 1080, 1920

        # Parse duration from "8s" format
        duration_seconds = int(inputs.duration.rstrip("s"))

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

    async def estimate_cost(self, inputs: Veo31FastInput) -> float:
        """Estimate cost for this generation in USD.

        Note: Pricing information not available in Fal documentation.
        Using placeholder value that should be updated with actual pricing.
        """
        # TODO: Update with actual pricing from Fal when available
        # Base cost, with 33% reduction if audio is disabled
        base_cost = 0.10  # Placeholder estimate for fast variant
        if not inputs.generate_audio:
            return base_cost * 0.67  # 33% discount
        return base_cost
