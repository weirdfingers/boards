"""
fal.ai ElevenLabs TTS Turbo v2.5 text-to-speech generator.

Generate high-speed text-to-speech audio using ElevenLabs TTS Turbo v2.5.
Converts written text into spoken audio with customizable voice, speed, and prosody parameters.

Based on Fal AI's fal-ai/elevenlabs/tts/turbo-v2.5 model.
See: https://fal.ai/models/fal-ai/elevenlabs/tts/turbo-v2.5
"""

import os

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class FalElevenlabsTtsTurboV25Input(BaseModel):
    """Input schema for ElevenLabs TTS Turbo v2.5 generation.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    text: str = Field(
        description="The text to convert to speech",
        min_length=1,
    )

    voice: str = Field(
        default="Rachel",
        description=(
            "Voice selection from predefined options (Aria, Roger, Sarah, Laura, Rachel, etc.)"
        ),
    )

    stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice stability (0-1)",
    )

    similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Voice similarity control (0-1)",
    )

    style: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Style exaggeration (0-1)",
    )

    speed: float = Field(
        default=1.0,
        ge=0.7,
        le=1.2,
        description="Speech tempo adjustment (0.7-1.2x)",
    )

    timestamps: bool = Field(
        default=False,
        description="Include word-level timing data in output",
    )

    language_code: str | None = Field(
        default=None,
        description="ISO 639-1 language code for language enforcement (Turbo v2.5 only)",
    )

    previous_text: str | None = Field(
        default=None,
        description="Prior context for speech continuity when concatenating generations",
    )

    next_text: str | None = Field(
        default=None,
        description="Subsequent context for speech continuity when concatenating generations",
    )


class FalElevenlabsTtsTurboV25Generator(BaseGenerator):
    """Generator for high-speed text-to-speech using ElevenLabs TTS Turbo v2.5."""

    name = "fal-elevenlabs-tts-turbo-v2-5"
    description = (
        "Fal: ElevenLabs TTS Turbo v2.5 - "
        "High-speed text-to-speech with customizable voices and prosody"
    )
    artifact_type = "audio"

    def get_input_schema(self) -> type[FalElevenlabsTtsTurboV25Input]:
        """Return the input schema for this generator."""
        return FalElevenlabsTtsTurboV25Input

    async def generate(
        self, inputs: FalElevenlabsTtsTurboV25Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using fal.ai ElevenLabs TTS Turbo v2.5."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalElevenlabsTtsTurboV25Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "text": inputs.text,
            "voice": inputs.voice,
            "stability": inputs.stability,
            "similarity_boost": inputs.similarity_boost,
            "style": inputs.style,
            "speed": inputs.speed,
            "timestamps": inputs.timestamps,
        }

        # Add optional fields only if provided
        if inputs.language_code is not None:
            arguments["language_code"] = inputs.language_code
        if inputs.previous_text is not None:
            arguments["previous_text"] = inputs.previous_text
        if inputs.next_text is not None:
            arguments["next_text"] = inputs.next_text

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/elevenlabs/tts/turbo-v2.5",
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

        # Extract audio URL from result
        # fal.ai returns: {"audio": {"url": "...", "content_type": "...", ...}}
        audio_data = result.get("audio")
        if audio_data is None:
            raise ValueError("No audio data returned from fal.ai API")

        audio_url = audio_data.get("url")
        if not audio_url:
            raise ValueError("Audio URL missing in fal.ai response")

        # Store audio result
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format="mp3",  # ElevenLabs TTS returns MP3 format
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: FalElevenlabsTtsTurboV25Input) -> float:
        """Estimate cost for ElevenLabs TTS Turbo v2.5 generation.

        ElevenLabs TTS Turbo v2.5 pricing is typically based on character count.
        Using a conservative estimate of $0.001 per character for turbo models.
        """
        # Calculate character count
        char_count = len(inputs.text)

        # Estimated cost: $0.001 per character (adjust based on actual pricing)
        # This is a placeholder - actual pricing should be verified
        return char_count * 0.001
