"""
LTX-2.3 Pro image-to-video generator.

A high-quality, fast AI video model that creates dynamic video content from
static images. Supports start and optional end frame, audio generation,
and resolutions up to 2160p.

Based on Fal AI's fal-ai/ltx-2.3/image-to-video model.
See: https://fal.ai/models/fal-ai/ltx-2.3/image-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Ltx23ImageToVideoInput(BaseModel):
    """Input schema for LTX-2.3 Pro image-to-video generation.

    Artifact fields (image) are automatically detected via type introspection
    and resolved from generation IDs to ImageArtifact objects.
    """

    image: ImageArtifact = Field(
        description="The image to use as the first frame for video generation"
    )
    prompt: str = Field(
        description="Text prompt describing the desired video motion.",
        min_length=1,
        max_length=5000,
    )
    end_image: ImageArtifact | None = Field(
        default=None,
        description="Optional end frame image. When provided, generates a transition "
        "video between the start and end frames.",
    )
    duration: Literal[6, 8, 10] = Field(
        default=6,
        description="Duration of the generated video in seconds",
    )
    resolution: Literal["1080p", "1440p", "2160p"] = Field(
        default="1080p",
        description="Resolution of the generated video",
    )
    aspect_ratio: Literal["auto", "16:9", "9:16"] = Field(
        default="auto",
        description="Aspect ratio of the generated video. 'auto' matches the input image.",
    )
    fps: Literal[24, 25, 48, 50] = Field(
        default=25,
        description="Frame rate of the generated video",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate audio for the video",
    )


class FalLtx23ImageToVideoGenerator(BaseGenerator):
    """Generator for creating videos from images using LTX-2.3 Pro."""

    name = "fal-ltx-23-image-to-video"
    description = (
        "Fal: LTX-2.3 Pro - Generate videos from images with motion guidance "
        "and optional end frame transitions"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[Ltx23ImageToVideoInput]:
        """Return the input schema for this generator."""
        return Ltx23ImageToVideoInput

    async def generate(
        self, inputs: Ltx23ImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai LTX-2.3 Pro image-to-video model."""
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalLtx23ImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        artifacts_to_upload = [inputs.image]
        if inputs.end_image is not None:
            artifacts_to_upload.append(inputs.end_image)

        image_urls = await upload_artifacts_to_fal(artifacts_to_upload, context)

        arguments: dict = {
            "image_url": image_urls[0],
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "resolution": inputs.resolution,
            "aspect_ratio": inputs.aspect_ratio,
            "fps": inputs.fps,
            "generate_audio": inputs.generate_audio,
        }

        if inputs.end_image is not None:
            arguments["end_image_url"] = image_urls[1]

        handler = await fal_client.submit_async(
            "fal-ai/ltx-2.3/image-to-video",
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
        # For "auto" aspect ratio, default to 16:9 dimensions as fallback
        aspect_for_lookup = inputs.aspect_ratio if inputs.aspect_ratio != "auto" else "16:9"
        default_width, default_height = resolution_dimensions.get(inputs.resolution, {}).get(
            aspect_for_lookup, (1920, 1080)
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

    async def estimate_cost(self, inputs: Ltx23ImageToVideoInput) -> float:
        """Estimate cost for LTX-2.3 Pro image-to-video generation.

        Estimated at $0.12 per 6-second video. Cost scales with duration.
        """
        base_cost = 0.12
        duration_multiplier = inputs.duration / 6
        return base_cost * duration_multiplier
