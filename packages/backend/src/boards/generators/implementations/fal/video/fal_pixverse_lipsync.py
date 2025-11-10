"""
PixVerse Lipsync video generator.

Generates realistic lip-synchronization animations by synchronizing video with
audio or text-to-speech. Supports optional audio input or TTS with customizable
voice selection.

Based on Fal AI's fal-ai/pixverse/lipsync model.
See: https://fal.ai/models/fal-ai/pixverse/lipsync
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, VideoArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class PixverseLipsyncInput(BaseModel):
    """Input schema for PixVerse Lipsync.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    video_url: VideoArtifact = Field(description="Input video source for lip-sync animation")
    audio_url: AudioArtifact | None = Field(
        default=None, description="Input audio file; if omitted, TTS generates audio from text"
    )
    text: str | None = Field(
        default=None,
        description="Content for text-to-speech synthesis (used when audio_url not provided)",
    )
    voice_id: Literal[
        "Emily",
        "James",
        "Isabella",
        "Liam",
        "Chloe",
        "Adrian",
        "Harper",
        "Ava",
        "Sophia",
        "Julia",
        "Mason",
        "Jack",
        "Oliver",
        "Ethan",
        "Auto",
    ] = Field(default="Auto", description="Voice selection for text-to-speech")


class FalPixverseLipsyncGenerator(BaseGenerator):
    """Generator for PixVerse lip-sync animation."""

    name = "fal-pixverse-lipsync"
    description = "Fal: PixVerse Lipsync - Realistic lip-sync animation with audio or TTS"
    artifact_type = "video"

    def get_input_schema(self) -> type[PixverseLipsyncInput]:
        """Return the input schema for this generator."""
        return PixverseLipsyncInput

    async def generate(
        self, inputs: PixverseLipsyncInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate lip-synced video using fal.ai pixverse/lipsync."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalPixverseLipsyncGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload video artifact to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        video_urls = await upload_artifacts_to_fal([inputs.video_url], context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "video_url": video_urls[0],
            "voice_id": inputs.voice_id,
        }

        # Add audio_url if provided, otherwise add text for TTS
        if inputs.audio_url is not None:
            audio_urls = await upload_artifacts_to_fal([inputs.audio_url], context)
            arguments["audio_url"] = audio_urls[0]
        elif inputs.text is not None:
            arguments["text"] = inputs.text
        else:
            raise ValueError("Either audio_url or text must be provided for lip-sync generation")

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/pixverse/lipsync",
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
        # fal.ai returns: {"video": {"url": "...", "content_type": "video/mp4", ...}}
        video_data = result.get("video")

        if not video_data:
            raise ValueError("No video returned from fal.ai API")

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError("Video missing URL in fal.ai response")

        # Extract format from content_type (e.g., "video/mp4" -> "mp4")
        content_type = video_data.get("content_type", "video/mp4")
        video_format = content_type.split("/")[-1] if "/" in content_type else "mp4"

        # Determine output duration
        # If audio provided, use its duration; otherwise use video duration
        output_duration = (
            inputs.audio_url.duration if inputs.audio_url is not None else inputs.video_url.duration
        )

        # Store the video result
        # Use input video dimensions and fps as they remain unchanged
        artifact = await context.store_video_result(
            storage_url=video_url,
            format=video_format,
            width=inputs.video_url.width,
            height=inputs.video_url.height,
            duration=output_duration,
            fps=inputs.video_url.fps,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: PixverseLipsyncInput) -> float:
        """Estimate cost for PixVerse Lipsync generation in USD.

        Pricing:
        - $0.04 per second of output video
        - $0.24 per 100 characters if using TTS (when text provided without audio)
        """
        # Base cost: $0.04 per second of video
        # Use input video duration as estimate for output duration
        video_duration_seconds = inputs.video_url.duration or 5.0  # Default to 5 seconds if unknown
        video_cost = video_duration_seconds * 0.04

        # Add TTS cost if using text instead of audio
        tts_cost = 0.0
        if inputs.audio_url is None and inputs.text is not None:
            # $0.24 per 100 characters
            text_length = len(inputs.text)
            tts_cost = (text_length / 100.0) * 0.24

        return video_cost + tts_cost
