"""
WAN-Pro 2.1 image-to-video generator.

A premium image-to-video model that generates high-quality 1080p videos at 30fps
with up to 6 seconds duration, converting static images into dynamic video content
with exceptional motion diversity.

Based on Fal AI's fal-ai/wan-pro/image-to-video model.
See: https://fal.ai/models/fal-ai/wan-pro/image-to-video
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class WanProImageToVideoInput(BaseModel):
    """Input schema for WAN-Pro 2.1 image-to-video generation.

    Artifact fields (image) are automatically detected via type introspection
    and resolved from generation IDs to ImageArtifact objects.
    """

    image: ImageArtifact = Field(description="The image to generate the video from")
    prompt: str = Field(description="Text prompt describing the desired video content and motion")
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility. If not specified, a random seed will be used",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Whether to enable the safety checker for content moderation",
    )


class FalWanProImageToVideoGenerator(BaseGenerator):
    """Generator for creating videos from static images using WAN-Pro 2.1."""

    name = "fal-wan-pro-image-to-video"
    description = "Fal: WAN-Pro 2.1 - Generate high-quality 1080p videos from static images"
    artifact_type = "video"

    def get_input_schema(self) -> type[WanProImageToVideoInput]:
        """Return the input schema for this generator."""
        return WanProImageToVideoInput

    async def generate(
        self, inputs: WanProImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai wan-pro/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalWanProImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "image_url": image_urls[0],
            "prompt": inputs.prompt,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Only add seed if provided (allow API to use random if not specified)
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/wan-pro/image-to-video",
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
        # WAN-Pro generates 1080p videos at 30fps with up to 6 seconds duration
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=1920,
            height=1080,
            duration=6,  # Maximum duration
            fps=30,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: WanProImageToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Note: Pricing information not available in Fal documentation.
        Using placeholder value that should be updated with actual pricing.
        """
        # TODO: Update with actual pricing from Fal when available
        return 0.10  # Placeholder estimate for premium image-to-video generation
