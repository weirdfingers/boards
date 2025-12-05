"""
fal.ai ElevenLabs Sound Effects V2 text-to-audio generator.

Generate sound effects from text descriptions using ElevenLabs advanced
sound effects model. Supports customizable duration, prompt influence,
and multiple output formats.

Based on Fal AI's fal-ai/elevenlabs/sound-effects/v2 model.
See: https://fal.ai/models/fal-ai/elevenlabs/sound-effects/v2
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ElevenlabsSoundEffectsV2Input(BaseModel):
    """Input schema for ElevenLabs Sound Effects V2 generation.

    Generates custom sound effects from natural language descriptions with
    configurable duration, prompt influence, and output format.
    """

    text: str = Field(
        description="Text describing the sound effect to generate",
        examples=[
            "Spacious braam suitable for high-impact movie trailer moments",
            "A gentle wind chime tinkling in a soft breeze",
        ],
    )
    duration_seconds: float | None = Field(
        default=None,
        ge=0.5,
        le=22.0,
        description=(
            "Duration in seconds (0.5-22). "
            "If None, optimal duration will be determined from prompt."
        ),
    )
    prompt_influence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="How closely to follow the prompt (0-1). Higher values mean less variation.",
    )
    output_format: Literal[
        "mp3_22050_32",
        "mp3_44100_32",
        "mp3_44100_64",
        "mp3_44100_96",
        "mp3_44100_128",
        "mp3_44100_192",
        "pcm_8000",
        "pcm_16000",
        "pcm_22050",
        "pcm_24000",
        "pcm_44100",
        "pcm_48000",
        "ulaw_8000",
        "alaw_8000",
        "opus_48000_32",
        "opus_48000_64",
        "opus_48000_96",
        "opus_48000_128",
        "opus_48000_192",
    ] = Field(
        default="mp3_44100_128",
        description=(
            "Output format of the generated audio. Formatted as codec_sample_rate_bitrate."
        ),
    )
    loop: bool = Field(
        default=False,
        description="Whether to create a sound effect that loops smoothly.",
    )


class FalElevenlabsSoundEffectsV2Generator(BaseGenerator):
    """ElevenLabs Sound Effects V2 text-to-audio generator using fal.ai."""

    name = "fal-elevenlabs-sound-effects-v2"
    artifact_type = "audio"
    description = (
        "Fal: ElevenLabs Sound Effects V2 - "
        "Generate custom sound effects from text descriptions with advanced AI"
    )

    def get_input_schema(self) -> type[ElevenlabsSoundEffectsV2Input]:
        return ElevenlabsSoundEffectsV2Input

    async def generate(
        self, inputs: ElevenlabsSoundEffectsV2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate sound effect using fal.ai ElevenLabs Sound Effects V2 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalElevenlabsSoundEffectsV2Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "text": inputs.text,
            "prompt_influence": inputs.prompt_influence,
            "output_format": inputs.output_format,
            "loop": inputs.loop,
        }

        # Only include duration_seconds if specified
        if inputs.duration_seconds is not None:
            arguments["duration_seconds"] = inputs.duration_seconds

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/elevenlabs/sound-effects/v2",
            arguments=arguments,
        )

        # Store the external job ID for tracking
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates (sample every 3rd event to avoid spam)
        from .....progress.models import ProgressUpdate

        event_count = 0
        async for event in handler.iter_events(with_logs=True):
            event_count += 1

            # Process every 3rd event to provide feedback without overwhelming
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

        # Extract audio URL from result
        # fal.ai returns: {"audio": {"url": "...", "content_type": "...", ...}}
        audio_data = result.get("audio")
        if audio_data is None:
            raise ValueError("No audio data returned from fal.ai API")

        audio_url = audio_data.get("url")
        if not audio_url:
            raise ValueError("Audio URL missing in fal.ai response")

        # Extract format from output_format (e.g., "mp3_44100_128" -> "mp3")
        format_parts = inputs.output_format.split("_")
        audio_format = format_parts[0] if format_parts else "mp3"

        # Store audio result
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format=audio_format,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: ElevenlabsSoundEffectsV2Input) -> float:
        """Estimate cost for ElevenLabs Sound Effects V2 generation.

        Based on typical ElevenLabs sound effects pricing.
        Cost is approximately $0.055 per sound effect generation.
        """
        # Fixed cost per generation regardless of duration or format
        return 0.055
