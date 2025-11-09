"""
fal.ai MiniMax Speech 2.6 Turbo text-to-speech generator.

Generate speech from text prompts using the MiniMax Speech-2.6 HD model,
which leverages advanced AI techniques to create high-quality text-to-speech.

Based on Fal AI's fal-ai/minimax/speech-2.6-turbo model.
See: https://fal.ai/models/fal-ai/minimax/speech-2.6-turbo
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class VoiceSetting(BaseModel):
    """Voice configuration settings."""

    voice_id: str = Field(
        default="Wise_Woman",
        description="Speaker identifier for the voice",
    )
    speed: float = Field(
        default=1.0,
        description="Playback speed multiplier",
    )
    pitch: float = Field(
        default=0.0,
        description="Pitch adjustment",
    )
    vol: float = Field(
        default=1.0,
        description="Volume level",
    )
    english_normalization: bool = Field(
        default=False,
        description="Enable English text normalization",
    )


class LoudnessNormalizationSetting(BaseModel):
    """Audio loudness normalization controls."""

    enabled: bool = Field(
        default=True,
        description="Enable loudness normalization",
    )
    target_loudness: float = Field(
        default=-18.0,
        ge=-70.0,
        le=-10.0,
        description="Target loudness in LUFS",
    )
    target_range: float = Field(
        default=8.0,
        ge=0.0,
        le=20.0,
        description="Target range in LU",
    )
    target_peak: float = Field(
        default=-0.5,
        ge=-3.0,
        le=0.0,
        description="Target peak level in dBTP",
    )


class MinimaxSpeech26TurboInput(BaseModel):
    """Input schema for MiniMax Speech 2.6 Turbo generation."""

    prompt: str = Field(
        description=(
            "Text to convert to speech " "(supports pause markers <#x#> with 0.01-99.99 seconds)"
        ),
        min_length=1,
        max_length=10000,
    )
    voice_setting: VoiceSetting = Field(
        default_factory=VoiceSetting,
        description="Voice configuration including voice_id, speed, pitch, volume",
    )
    language_boost: str = Field(
        default="auto",
        description=(
            "Enhance recognition of specified languages and dialects "
            "(auto or specific language code)"
        ),
    )
    output_format: Literal["url", "hex"] = Field(
        default="url",
        description="Output format: 'url' for audio file URL or 'hex' for hex-encoded data",
    )
    normalization_setting: LoudnessNormalizationSetting = Field(
        default_factory=LoudnessNormalizationSetting,
        description="Audio loudness normalization controls",
    )


class FalMinimaxSpeech26TurboGenerator(BaseGenerator):
    """MiniMax Speech 2.6 Turbo text-to-speech generator using fal.ai."""

    name = "fal-minimax-speech-2-6-turbo"
    artifact_type = "audio"
    description = (
        "Fal: MiniMax Speech 2.6 Turbo - "
        "High-quality text-to-speech with customizable voices and 35+ languages"
    )

    def get_input_schema(self) -> type[MinimaxSpeech26TurboInput]:
        return MinimaxSpeech26TurboInput

    async def generate(
        self, inputs: MinimaxSpeech26TurboInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using fal.ai MiniMax Speech 2.6 Turbo model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalMinimaxSpeech26TurboGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "voice_setting": {
                "voice_id": inputs.voice_setting.voice_id,
                "speed": inputs.voice_setting.speed,
                "pitch": inputs.voice_setting.pitch,
                "vol": inputs.voice_setting.vol,
                "english_normalization": inputs.voice_setting.english_normalization,
            },
            "language_boost": inputs.language_boost,
            "output_format": inputs.output_format,
            "normalization_setting": {
                "enabled": inputs.normalization_setting.enabled,
                "target_loudness": inputs.normalization_setting.target_loudness,
                "target_range": inputs.normalization_setting.target_range,
                "target_peak": inputs.normalization_setting.target_peak,
            },
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/minimax/speech-2.6-turbo",
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
            format="mp3",  # MiniMax Speech returns MP3 format
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: MinimaxSpeech26TurboInput) -> float:
        """Estimate cost for MiniMax Speech 2.6 Turbo generation.

        MiniMax Speech 2.6 Turbo costs $0.06 per 1000 characters.
        """
        # Calculate character count
        char_count = len(inputs.prompt)

        # Cost is $0.06 per 1000 characters
        return (char_count / 1000.0) * 0.06
