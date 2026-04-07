"""
xAI Grok Imagine Video extend-video generator.

Extends an existing video by generating additional content based on a text prompt.
The output is the original video with the extension stitched together.

Based on Fal AI's xai/grok-imagine-video/extend-video model.
See: https://fal.ai/models/xai/grok-imagine-video/extend-video
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import VideoArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class GrokImagineVideoExtendVideoInput(BaseModel):
    """Input schema for Grok Imagine Video extend-video generation.

    Artifact fields (video) are automatically detected via type
    introspection and resolved from generation IDs to VideoArtifact objects.
    """

    prompt: str = Field(
        max_length=4096,
        description="Text description of what should happen next in the video",
    )
    video: VideoArtifact = Field(
        description="Source video to extend (MP4, 2-15 seconds long)",
    )
    duration: int = Field(
        default=6,
        ge=2,
        le=10,
        description="Length of the extension in seconds (2-10)",
    )


class FalGrokImagineVideoExtendVideoGenerator(BaseGenerator):
    """Generator for extending videos using xAI Grok Imagine Video."""

    name = "fal-grok-imagine-video-extend-video"
    description = "Fal: Grok Imagine Video - Extend an existing video with AI-generated content"
    artifact_type = "video"

    def get_input_schema(self) -> type[GrokImagineVideoExtendVideoInput]:
        """Return the input schema for this generator."""
        return GrokImagineVideoExtendVideoInput

    async def generate(
        self, inputs: GrokImagineVideoExtendVideoInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate extended video using fal.ai xai/grok-imagine-video/extend-video."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGrokImagineVideoExtendVideoGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload video artifact to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        video_urls = await upload_artifacts_to_fal([inputs.video], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "video_url": video_urls[0],
            "duration": inputs.duration,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "xai/grok-imagine-video/extend-video",
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

        # Get final result
        result = await handler.get()

        # Extract video from result
        video_data = result.get("video")
        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Use input video dimensions for the output (extension preserves dimensions)
        width = inputs.video.width
        height = inputs.video.height

        # Total duration = original + extension
        original_duration = inputs.video.duration or 0
        total_duration = original_duration + inputs.duration

        artifact = await context.store_video_result(
            storage_url=video_url,
            format="mp4",
            width=width,
            height=height,
            duration=total_duration,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: GrokImagineVideoExtendVideoInput) -> float:
        """Estimate cost for this generation in USD.

        Based on Fal pricing: ~$0.05/second video output + ~$0.01/second video input.
        """
        input_duration = inputs.video.duration or 0
        return 0.05 * inputs.duration + 0.01 * input_duration
