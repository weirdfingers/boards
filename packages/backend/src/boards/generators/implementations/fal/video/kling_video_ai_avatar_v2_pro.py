"""
fal.ai Kling Video AI Avatar v2 Pro generator.

Transforms static portrait images into synchronized talking avatar videos
with audio-driven facial animation. Supports realistic humans, animals,
cartoons, and stylized figures.

Based on Fal AI's fal-ai/kling-video/ai-avatar/v2/pro model.
See: https://fal.ai/models/fal-ai/kling-video/ai-avatar/v2/pro
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KlingVideoAiAvatarV2ProInput(BaseModel):
    """Input schema for kling-video/ai-avatar/v2/pro.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    image: ImageArtifact = Field(description="The image to use as your avatar")
    audio: AudioArtifact = Field(description="The audio file for lip-sync animation")
    prompt: str = Field(
        default=".",
        description="Optional prompt to refine animation details",
    )


class FalKlingVideoAiAvatarV2ProGenerator(BaseGenerator):
    """Generator for AI avatar talking videos using Kling Video AI Avatar v2 Pro."""

    name = "fal-kling-video-ai-avatar-v2-pro"
    description = (
        "Fal: Kling Video AI Avatar v2 Pro - "
        "Transform portraits into talking avatar videos with audio-driven facial animation"
    )
    artifact_type = "video"

    def get_input_schema(self) -> type[KlingVideoAiAvatarV2ProInput]:
        """Return the input schema for this generator."""
        return KlingVideoAiAvatarV2ProInput

    async def generate(
        self, inputs: KlingVideoAiAvatarV2ProInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate talking avatar video using fal.ai kling-video/ai-avatar/v2/pro."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKlingVideoAiAvatarV2ProGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image and audio artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        # Upload image and audio separately
        image_urls = await upload_artifacts_to_fal([inputs.image], context)
        audio_urls = await upload_artifacts_to_fal([inputs.audio], context)

        # Prepare arguments for fal.ai API
        arguments: dict[str, str] = {
            "image_url": image_urls[0],
            "audio_url": audio_urls[0],
            "prompt": inputs.prompt,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling-video/ai-avatar/v2/pro",
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
        # fal.ai returns: {"video": {"url": "...", "content_type": "..."}, "duration": ...}
        video_data = result.get("video")

        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract format from content_type (e.g., "video/mp4" -> "mp4")
        content_type = video_data.get("content_type", "video/mp4")
        if content_type.startswith("video/"):
            video_format = content_type.split("/")[-1]
        else:
            # Default to mp4 if content_type is not a video mime type
            video_format = "mp4"

        # Get duration from result if available
        duration = result.get("duration")

        # Store the video result
        # Note: The API doesn't return width/height/fps, so we use reasonable defaults
        artifact = await context.store_video_result(
            storage_url=video_url,
            format=video_format,
            width=None,
            height=None,
            duration=duration,
            fps=None,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: KlingVideoAiAvatarV2ProInput) -> float:
        """Estimate cost for this generation in USD.

        Pricing: $0.115 per second of generated video.
        Cost depends on audio duration since the output video matches audio length.
        """
        # If audio duration is available, calculate based on that
        if inputs.audio.duration is not None:
            return 0.115 * inputs.audio.duration

        # Default estimate for unknown duration (assume ~10 second video)
        return 1.15
