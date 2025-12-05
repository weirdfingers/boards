"""
MiniMax Hailuo 2.3 Pro image-to-video generator.

Advanced image-to-video generation model with 1080p resolution. Transforms static
images into dynamic videos using text prompts to guide the creative output.

Based on Fal AI's fal-ai/minimax/hailuo-2.3/pro/image-to-video model.
See: https://fal.ai/models/fal-ai/minimax/hailuo-2.3/pro/image-to-video
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class MinimaxHailuo23ProImageToVideoInput(BaseModel):
    """Input schema for MiniMax Hailuo 2.3 Pro image-to-video generation.

    Artifact fields (image_url) are automatically detected via type introspection
    and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="Text prompt for video generation",
        min_length=1,
        max_length=2000,
    )
    image_url: ImageArtifact = Field(description="URL of the image to use as the first frame")
    prompt_optimizer: bool = Field(
        default=True,
        description="Whether to use the model's prompt optimizer",
    )


class FalMinimaxHailuo23ProImageToVideoGenerator(BaseGenerator):
    """Generator for creating videos from images using MiniMax Hailuo 2.3 Pro."""

    name = "fal-minimax-hailuo-2-3-pro-image-to-video"
    description = "Fal: MiniMax Hailuo 2.3 Pro - Image-to-video with 1080p resolution"
    artifact_type = "video"

    def get_input_schema(self) -> type[MinimaxHailuo23ProImageToVideoInput]:
        """Return the input schema for this generator."""
        return MinimaxHailuo23ProImageToVideoInput

    async def generate(
        self, inputs: MinimaxHailuo23ProImageToVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using fal.ai minimax/hailuo-2.3/pro/image-to-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalMinimaxHailuo23ProImageToVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": image_urls[0],
            "prompt_optimizer": inputs.prompt_optimizer,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/minimax/hailuo-2.3/pro/image-to-video",
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
        # so we'll use defaults based on the model's 1080p output
        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=1920,
            height=1080,
            duration=None,  # Duration not provided in response
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: MinimaxHailuo23ProImageToVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Note: Pricing information not available in Fal documentation.
        Using placeholder value that should be updated with actual pricing.
        """
        # TODO: Update with actual pricing from Fal when available
        return 0.12  # Placeholder estimate for 1080p video generation
