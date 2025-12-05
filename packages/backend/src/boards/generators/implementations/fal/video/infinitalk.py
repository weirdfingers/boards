"""
fal.ai infinitalk video generator.

Generates talking avatar videos from an image and audio file. The avatar
lip-syncs to the provided audio with natural facial expressions.

Based on Fal AI's fal-ai/infinitalk model.
See: https://fal.ai/models/fal-ai/infinitalk
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class InfinitalkInput(BaseModel):
    """Input schema for infinitalk.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    image: ImageArtifact = Field(
        description=(
            "Input image for the avatar. "
            "If the aspect ratio doesn't match, it is resized and center cropped"
        )
    )
    audio: AudioArtifact = Field(description="Audio file to synchronize with the avatar")
    prompt: str = Field(description="Text prompt to guide video generation")
    num_frames: int = Field(
        default=145,
        ge=41,
        le=721,
        description="Number of frames to generate",
    )
    resolution: Literal["480p", "720p"] = Field(
        default="480p",
        description="Output video resolution",
    )
    acceleration: Literal["none", "regular", "high"] = Field(
        default="regular",
        description="Acceleration level for generation speed",
    )
    seed: int = Field(
        default=42,
        description="Seed for reproducibility",
    )


class FalInfinitalkGenerator(BaseGenerator):
    """Generator for talking avatar videos from image and audio."""

    name = "fal-infinitalk"
    description = "Fal: infinitalk - Generate talking avatar video from image and audio"
    artifact_type = "video"

    def get_input_schema(self) -> type[InfinitalkInput]:
        """Return the input schema for this generator."""
        return InfinitalkInput

    async def generate(
        self, inputs: InfinitalkInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate talking avatar video using fal.ai infinitalk."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalInfinitalkGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image and audio artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        # Upload image and audio separately
        image_urls = await upload_artifacts_to_fal([inputs.image], context)
        audio_urls = await upload_artifacts_to_fal([inputs.audio], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "image_url": image_urls[0],
            "audio_url": audio_urls[0],
            "prompt": inputs.prompt,
            "num_frames": inputs.num_frames,
            "resolution": inputs.resolution,
            "acceleration": inputs.acceleration,
            "seed": inputs.seed,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/infinitalk",
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
        # fal.ai returns: {"video": {"url": "...", "content_type": "video/mp4", ...}, "seed": 42}
        video_data = result.get("video")

        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract format from content_type (e.g., "video/mp4" -> "mp4")
        # Infinitalk always produces MP4 videos, so default to mp4
        content_type = video_data.get("content_type", "video/mp4")
        if content_type.startswith("video/"):
            video_format = content_type.split("/")[-1]
        else:
            # If content_type is not a video mime type (e.g., application/octet-stream),
            # default to mp4 since infinitalk only produces mp4 videos
            video_format = "mp4"

        # Store the video result
        # Use input image dimensions and audio duration for metadata
        # Estimate FPS based on num_frames and audio duration
        fps = 30.0  # Default FPS
        if inputs.audio.duration and inputs.audio.duration > 0:
            fps = inputs.num_frames / inputs.audio.duration

        # Parse resolution to get dimensions
        width, height = self._parse_resolution(inputs.resolution)

        artifact = await context.store_video_result(
            storage_url=video_url,
            format=video_format,
            width=width,
            height=height,
            duration=inputs.audio.duration,
            fps=int(fps),
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    def _parse_resolution(self, resolution: str) -> tuple[int, int]:
        """Parse resolution string to width and height.

        Args:
            resolution: Resolution string like "480p" or "720p"

        Returns:
            Tuple of (width, height)
        """
        if resolution == "480p":
            return (854, 480)
        elif resolution == "720p":
            return (1280, 720)
        else:
            # Default to 480p
            return (854, 480)

    async def estimate_cost(self, inputs: InfinitalkInput) -> float:
        """Estimate cost for infinitalk generation in USD.

        Pricing not specified in documentation, using estimate based on
        typical video generation costs. Higher resolution and more frames
        may increase cost.
        """
        # Base cost estimate per generation
        base_cost = 0.10

        # Adjust for resolution
        if inputs.resolution == "720p":
            base_cost *= 1.5

        # Adjust for frame count (more frames = higher cost)
        # Base estimate is for 145 frames
        frame_multiplier = inputs.num_frames / 145.0
        base_cost *= frame_multiplier

        return base_cost
