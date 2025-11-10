"""
Google Veo 3.1 reference-to-video generator.

Generates videos from multiple reference images to maintain consistent subject
appearance while creating dynamic video content based on text prompts.

Based on Fal AI's fal-ai/veo3.1/reference-to-video model.
See: https://fal.ai/models/fal-ai/veo3.1/reference-to-video
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Veo31ReferenceToVideoInput(BaseModel):
    """Input schema for Veo 3.1 reference-to-video generation.

    Artifact fields (image_urls) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    image_urls: list[ImageArtifact] = Field(
        description="URLs of reference images for consistent subject appearance"
    )
    prompt: str = Field(description="Text description of desired video content")
    duration: Literal["8s"] = Field(
        default="8s",
        description="Duration of the generated video in seconds (currently only 8s is supported)",
    )
    resolution: Literal["720p", "1080p"] = Field(
        default="720p",
        description="Resolution of the generated video",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate audio for the video. Disabling uses 50% fewer credits",
    )


class FalVeo31ReferenceToVideoGenerator(BaseGenerator):
    """Generator for creating videos from reference images using Google Veo 3.1."""

    name = "fal-veo31-reference-to-video"
    description = "Fal: Veo 3.1 - Generate videos from reference images with consistent subjects"
    artifact_type = "video"

    def get_input_schema(self) -> type[Veo31ReferenceToVideoInput]:
        """Return the input schema for this generator."""
        return Veo31ReferenceToVideoInput

    async def generate(
        self, inputs: Veo31ReferenceToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai veo3.1/reference-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalVeo31ReferenceToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        reference_image_urls = await upload_artifacts_to_fal(inputs.image_urls, context)

        # Prepare arguments for fal.ai API
        arguments = {
            "image_urls": reference_image_urls,
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "resolution": inputs.resolution,
            "generate_audio": inputs.generate_audio,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/veo3.1/reference-to-video",
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

        # Store video result
        # Note: Fal API doesn't provide video dimensions/duration in the response,
        # so we'll use defaults based on input parameters
        width = 1280 if inputs.resolution == "720p" else 1920
        height = 720 if inputs.resolution == "720p" else 1080

        # Parse duration from "8s" format
        duration_seconds = int(inputs.duration.rstrip("s"))

        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=duration_seconds,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: Veo31ReferenceToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Note: Pricing information not available in Fal documentation.
        Using placeholder value that should be updated with actual pricing.
        """
        # TODO: Update with actual pricing from Fal when available
        # Base cost, with 50% reduction if audio is disabled
        base_cost = 0.15  # Placeholder estimate
        if not inputs.generate_audio:
            return base_cost * 0.5
        return base_cost
