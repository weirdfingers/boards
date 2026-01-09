"""
fal.ai Chatterbox Text-to-Speech Turbo generator.

Generate expressive speech from text with paralinguistic controls like laughs,
sighs, coughs, and more. Supports voice cloning with custom audio samples.

Based on Fal AI's fal-ai/chatterbox/text-to-speech/turbo model.
See: https://fal.ai/models/fal-ai/chatterbox/text-to-speech/turbo
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult

# Voice presets available in Chatterbox
ChatterboxVoice = Literal[
    "aaron",
    "abigail",
    "anaya",
    "andy",
    "archer",
    "brian",
    "chloe",
    "dylan",
    "emmanuel",
    "ethan",
    "evelyn",
    "gavin",
    "gordon",
    "ivan",
    "laura",
    "lucy",
    "madison",
    "marisol",
    "meera",
    "walter",
]


class ChatterboxTtsTurboInput(BaseModel):
    """Input schema for Chatterbox TTS Turbo.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    text: str = Field(
        description=(
            "The text to be converted to speech. Supports paralinguistic tags: "
            "[clear throat], [sigh], [shush], [cough], [groan], [sniff], [gasp], "
            "[chuckle], [laugh]"
        ),
        min_length=1,
    )
    voice: ChatterboxVoice = Field(
        default="lucy",
        description="Preset voice to use for synthesis",
    )
    audio_url: AudioArtifact | None = Field(
        default=None,
        description=(
            "Optional audio file (5-10 seconds) for voice cloning. "
            "If provided, this overrides the preset voice selection."
        ),
    )
    temperature: float = Field(
        default=0.8,
        ge=0.05,
        le=2.0,
        description="Temperature for generation. Higher values create more varied speech patterns.",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible results. Set for consistent generations.",
    )


class FalChatterboxTtsTurboGenerator(BaseGenerator):
    """Chatterbox TTS Turbo text-to-speech generator using fal.ai."""

    name = "fal-chatterbox-tts-turbo"
    artifact_type = "audio"
    description = (
        "Fal: Chatterbox TTS Turbo - "
        "Expressive text-to-speech with paralinguistic controls and voice cloning"
    )

    def get_input_schema(self) -> type[ChatterboxTtsTurboInput]:
        return ChatterboxTtsTurboInput

    async def generate(
        self, inputs: ChatterboxTtsTurboInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using fal.ai Chatterbox TTS Turbo model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalChatterboxTtsTurboGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict[str, str | float | int] = {
            "text": inputs.text,
            "voice": inputs.voice,
            "temperature": inputs.temperature,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Handle voice cloning audio upload
        if inputs.audio_url is not None:
            from ..utils import upload_artifacts_to_fal

            audio_urls = await upload_artifacts_to_fal([inputs.audio_url], context)
            arguments["audio_url"] = audio_urls[0]

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/chatterbox/text-to-speech/turbo",
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
        # fal.ai returns: {"audio": {"url": "..."}}
        audio_data = result.get("audio")
        if audio_data is None:
            raise ValueError("No audio data returned from fal.ai API")

        audio_url = audio_data.get("url")
        if not audio_url:
            raise ValueError("Audio URL missing in fal.ai response")

        # Store audio result
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format="wav",  # Chatterbox TTS returns WAV format
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: ChatterboxTtsTurboInput) -> float:
        """Estimate cost for Chatterbox TTS Turbo generation.

        Chatterbox TTS Turbo pricing is approximately $0.03 per generation.
        """
        return 0.03
