"""
WAN 2.5 Preview image-to-video generator.

An image-to-video generation model that creates dynamic video content from static
images using text prompts to guide motion and camera movement. Supports durations
of 5 or 10 seconds at 480p, 720p, or 1080p resolution.

Based on Fal AI's fal-ai/wan-25-preview/image-to-video model.
See: https://fal.ai/models/fal-ai/wan-25-preview/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Wan25PreviewImageToVideoInput(BaseModel):
    """Input schema for WAN 2.5 Preview image-to-video generation.

    Artifact fields (image) are automatically detected via type introspection
    and resolved from generation IDs to ImageArtifact objects.
    """

    image: ImageArtifact = Field(
        description="The image to use as the first frame for video generation"
    )
    prompt: str = Field(
        description="The text prompt describing the desired video motion. Max 800 characters.",
        max_length=800,
    )
    duration: Literal["5", "10"] = Field(
        default="5",
        description="Duration of the generated video in seconds",
    )
    resolution: Literal["480p", "720p", "1080p"] = Field(
        default="1080p",
        description="Resolution of the generated video",
    )
    audio_url: str | None = Field(
        default=None,
        description=(
            "URL of a WAV or MP3 audio file (3-30 seconds, max 15MB) for background music. "
            "Audio is truncated or padded to match video duration."
        ),
    )
    seed: int | None = Field(
        default=None,
        description=(
            "Random seed for reproducibility. If not specified, a random seed will be used."
        ),
    )
    negative_prompt: str | None = Field(
        default=None,
        description="Content to avoid in the generated video. Max 500 characters.",
        max_length=500,
    )
    enable_prompt_expansion: bool = Field(
        default=True,
        description="Enable LLM-based prompt rewriting to improve results",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable content safety filtering",
    )


class FalWan25PreviewImageToVideoGenerator(BaseGenerator):
    """Generator for creating videos from static images using WAN 2.5 Preview."""

    name = "fal-wan-25-preview-image-to-video"
    description = "Fal: WAN 2.5 Preview - Generate videos from images with motion guidance"
    artifact_type = "video"

    def get_input_schema(self) -> type[Wan25PreviewImageToVideoInput]:
        """Return the input schema for this generator."""
        return Wan25PreviewImageToVideoInput

    async def generate(
        self, inputs: Wan25PreviewImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai wan-25-preview/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalWan25PreviewImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image], context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "image_url": image_urls[0],
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "resolution": inputs.resolution,
            "enable_prompt_expansion": inputs.enable_prompt_expansion,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Only add optional parameters if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        if inputs.negative_prompt is not None:
            arguments["negative_prompt"] = inputs.negative_prompt

        if inputs.audio_url is not None:
            arguments["audio_url"] = inputs.audio_url

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/wan-25-preview/image-to-video",
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
        # Expected structure: {"video": {"url": "...", "width": ..., "height": ..., ...}}
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Get video dimensions based on resolution setting
        resolution_map = {
            "480p": (854, 480),
            "720p": (1280, 720),
            "1080p": (1920, 1080),
        }
        default_width, default_height = resolution_map.get(inputs.resolution, (1920, 1080))

        # Use actual dimensions from response if available, otherwise use defaults
        width = video_data.get("width", default_width)
        height = video_data.get("height", default_height)
        fps = video_data.get("fps", 30)
        duration = video_data.get("duration", int(inputs.duration))

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

    async def estimate_cost(self, inputs: Wan25PreviewImageToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Note: Pricing information not available in Fal documentation.
        Using placeholder value that should be updated with actual pricing.
        """
        # TODO: Update with actual pricing from Fal when available
        # Estimate based on duration - longer videos cost more
        base_cost = 0.10
        if inputs.duration == "10":
            return base_cost * 2.0  # 10 second videos cost more
        return base_cost
