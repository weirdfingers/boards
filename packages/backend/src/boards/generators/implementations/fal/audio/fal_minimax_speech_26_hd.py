"""
Text-to-speech generation using Minimax Speech 2.6-HD.

Based on Fal AI's fal-ai/minimax/speech-2.6-hd model.
See: https://fal.ai/models/fal-ai/minimax/speech-2.6-hd
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class VoiceSetting(BaseModel):
    """Voice settings for speech synthesis."""

    voice_id: str = Field(
        default="Wise_Woman",
        description="Voice ID from predefined voices (e.g., Wise_Woman, Young_Man, etc.)",
    )
    speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech speed multiplier (0.5-2.0)",
    )
    vol: float = Field(
        default=1.0,
        ge=0.01,
        le=10.0,
        description="Volume level (0.01-10)",
    )
    pitch: int = Field(
        default=0,
        ge=-12,
        le=12,
        description="Pitch adjustment in semitones (-12 to 12)",
    )
    emotion: str | None = Field(
        default=None,
        description=(
            "Emotion for speech (happy, sad, angry, fearful, disgusted, surprised, neutral)"
        ),
    )
    english_normalization: bool = Field(
        default=False,
        description="Enable English text normalization",
    )


class AudioSetting(BaseModel):
    """Audio output settings."""

    format: Literal["mp3", "pcm", "flac"] = Field(
        default="mp3",
        description="Output audio format",
    )
    sample_rate: Literal[8000, 16000, 22050, 24000, 32000, 44100] = Field(
        default=32000,
        description="Sample rate in Hz",
    )
    channel: Literal[1, 2] = Field(
        default=1,
        description="Number of audio channels (1=mono, 2=stereo)",
    )
    bitrate: Literal[32000, 64000, 128000, 256000] = Field(
        default=128000,
        description="Audio bitrate in bits per second",
    )


class NormalizationSetting(BaseModel):
    """Audio normalization settings."""

    enabled: bool = Field(
        default=True,
        description="Enable audio normalization",
    )
    target_loudness: float = Field(
        default=-18.0,
        ge=-70.0,
        le=-10.0,
        description="Target loudness in LUFS (-70 to -10)",
    )
    target_range: float = Field(
        default=8.0,
        ge=0.0,
        le=20.0,
        description="Target loudness range in LU (0-20)",
    )
    target_peak: float = Field(
        default=-0.5,
        ge=-3.0,
        le=0.0,
        description="Target peak level in dBTP (-3 to 0)",
    )


class FalMinimaxSpeech26HdInput(BaseModel):
    """Input schema for Fal Minimax Speech 2.6-HD generator."""

    prompt: str = Field(
        description=(
            "Text to convert to speech. Paragraph breaks should be marked with newline characters."
        ),
        min_length=1,
        max_length=10000,
    )
    language_boost: str | None = Field(
        default=None,
        description=(
            "Language boost option. Supports: Chinese, English, Arabic, Russian, Spanish, "
            "French, Portuguese, German, Turkish, Dutch, Ukrainian, Vietnamese, Indonesian, "
            "Japanese, Italian, Korean, Thai, Polish, Romanian, Greek, Czech, Finnish, Hindi, "
            "Bulgarian, Danish, Hebrew, Malay, Slovak, Swedish, Croatian, Hungarian, "
            "Norwegian, Slovenian, Catalan, Nynorsk, Afrikaans"
        ),
    )
    output_format: Literal["hex", "url"] = Field(
        default="url",
        description=(
            "Output format for audio data (url returns a downloadable link, hex returns raw data)"
        ),
    )
    voice_setting: VoiceSetting = Field(
        default_factory=VoiceSetting,
        description="Voice customization settings",
    )
    audio_setting: AudioSetting = Field(
        default_factory=AudioSetting,
        description="Audio output format settings",
    )
    normalization_setting: NormalizationSetting = Field(
        default_factory=NormalizationSetting,
        description="Audio normalization settings",
    )


class FalMinimaxSpeech26HdGenerator(BaseGenerator):
    """Generator for text-to-speech using Minimax Speech 2.6-HD."""

    name = "fal-minimax-speech-26-hd"
    description = (
        "High-quality text-to-speech generation with extensive voice customization options"
    )
    artifact_type = "audio"

    def get_input_schema(self) -> type[FalMinimaxSpeech26HdInput]:
        """Return the input schema for this generator."""
        return FalMinimaxSpeech26HdInput

    async def generate(
        self, inputs: FalMinimaxSpeech26HdInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using fal.ai minimax/speech-2.6-hd."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalMinimaxSpeech26HdGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "output_format": inputs.output_format,
            "voice_setting": inputs.voice_setting.model_dump(exclude_none=True),
            "audio_setting": inputs.audio_setting.model_dump(),
            "normalization_setting": inputs.normalization_setting.model_dump(),
        }

        # Only add language_boost if specified
        if inputs.language_boost:
            arguments["language_boost"] = inputs.language_boost

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/minimax/speech-2.6-hd",
            arguments=arguments,
        )

        # Store external job ID
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates
        from .....progress.models import ProgressUpdate

        event_count = 0
        async for _event in handler.iter_events(with_logs=True):
            event_count += 1
            # Sample every 3rd event to avoid spam
            if event_count % 3 == 0:
                await context.publish_progress(
                    ProgressUpdate(
                        job_id=handler.request_id,
                        status="processing",
                        progress=50.0,
                        phase="processing",
                    )
                )

        # Get final result
        result = await handler.get()

        # Extract audio output
        audio_data = result.get("audio")
        if audio_data is None:
            raise ValueError("No audio data returned from API")

        if not isinstance(audio_data, dict):
            raise ValueError(f"Unexpected audio data type: {type(audio_data)}")

        audio_url = audio_data.get("url")
        if not audio_url:
            raise ValueError("Audio URL missing")

        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format=inputs.audio_setting.format,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: FalMinimaxSpeech26HdInput) -> float:
        """Estimate cost for this generation in USD."""
        # Minimax Speech 2.6-HD pricing (estimated at $0.015 per generation)
        # This is a reasonable estimate for TTS models
        return 0.015
