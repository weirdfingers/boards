"""
fal.ai Kling Video AI Avatar v2 Standard generator.

Generates avatar videos by synthesizing realistic humans, animals, cartoons, or
stylized characters. Takes an image and audio as inputs to create synchronized
video output.

Based on Fal AI's fal-ai/kling-video/ai-avatar/v2/standard model.
See: https://fal.ai/models/fal-ai/kling-video/ai-avatar/v2/standard
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingVideoAiAvatarV2StandardInput(BaseModel):
    """Input schema for Kling Video AI Avatar v2 Standard.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    image: ImageArtifact = Field(description="The image to use as your avatar")
    audio: AudioArtifact = Field(description="The audio file for lip-sync animation")
    prompt: str | None = Field(
        default=".", description="The prompt to use for the video generation"
    )


class FalKlingVideoAiAvatarV2StandardGenerator(BaseGenerator):
    """Generator for AI-powered avatar video synthesis."""

    name = "fal-kling-video-ai-avatar-v2-standard"
    description = "Fal: Kling Video AI Avatar v2 Standard - Avatar video from image and audio"
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingVideoAiAvatarV2StandardInput]:
        """Return the input schema for this generator."""
        return KlingVideoAiAvatarV2StandardInput

    async def generate(
        self, inputs: KlingVideoAiAvatarV2StandardInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate avatar video using fal.ai kling-video/ai-avatar/v2/standard."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingVideoAiAvatarV2StandardGenerator. "
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
        }

        # Add prompt only if provided and not the default empty value
        if inputs.prompt and inputs.prompt != ".":
            arguments["prompt"] = inputs.prompt

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/ai-avatar/v2/standard",
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
        # fal.ai returns: {"video": {"url": ..., "content_type": ...}, "duration": ...}
        video_data = result.get("video")

        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract format from content_type (e.g., "video/mp4" -> "mp4")
        content_type = video_data.get("content_type", "video/mp4")
        video_format = content_type.split("/")[-1] if "/" in content_type else "mp4"

        # Extract duration from response (available in API response)
        duration = result.get("duration")

        # Store the video result
        # Use input image dimensions as base dimensions (avatar video maintains aspect ratio)
        artifact = await context.store_video_result(
            storage_url=video_url,
            format=video_format,
            width=inputs.image.width,
            height=inputs.image.height,
            duration=duration,
            fps=None,  # Not provided by API
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: KlingVideoAiAvatarV2StandardInput) -> float:
        """Estimate cost for Kling Video AI Avatar v2 Standard generation in USD.

        Pricing not specified in documentation, using estimate based on
        typical Kling video generation costs.
        """
        # Estimate per generation based on typical Kling pricing
        return 0.10
