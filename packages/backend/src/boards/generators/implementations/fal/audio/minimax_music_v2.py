"""
fal.ai minimax-music/v2 text-to-music generator.

Generate music from text prompts using the MiniMax Music 2.0 model, which leverages
advanced AI techniques to create high-quality, diverse musical compositions.

Based on Fal AI's fal-ai/minimax-music/v2 model.
See: https://fal.ai/models/fal-ai/minimax-music/v2
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class AudioSetting(BaseModel):
    """Audio output settings for minimax-music/v2."""

    format: Literal["mp3", "pcm", "flac"] = Field(
        default="mp3",
        description="Audio output format",
    )
    sample_rate: Literal[8000, 16000, 22050, 24000, 32000, 44100] = Field(
        default=44100,
        description="Audio sample rate in Hz",
    )
    bitrate: Literal[32000, 64000, 128000, 256000] = Field(
        default=256000,
        description="Audio bitrate in bits per second",
    )


class MinimaxMusicV2Input(BaseModel):
    """Input schema for minimax-music/v2 music generation."""

    prompt: str = Field(
        description="A description of the music, specifying style, mood, and scenario",
        min_length=10,
        max_length=300,
    )
    lyrics_prompt: str = Field(
        description=(
            "Lyrics of the song. Use \\n to separate lines. "
            "Structure tags like [Intro], [Verse], [Chorus] supported"
        ),
        min_length=10,
        max_length=3000,
    )
    audio_setting: AudioSetting | None = Field(
        default=None,
        description="Audio output settings (format, sample rate, bitrate)",
    )


class FalMinimaxMusicV2Generator(BaseGenerator):
    """minimax-music/v2 music generator using fal.ai."""

    name = "fal-minimax-music-v2"
    artifact_type = "audio"
    description = "Fal: MiniMax Music 2.0 - generate music from text prompts and lyrics"

    def get_input_schema(self) -> type[MinimaxMusicV2Input]:
        return MinimaxMusicV2Input

    async def generate(
        self, inputs: MinimaxMusicV2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate music using fal.ai minimax-music/v2 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalMinimaxMusicV2Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        from typing import Any

        arguments: dict[str, Any] = {
            "prompt": inputs.prompt,
            "lyrics_prompt": inputs.lyrics_prompt,
        }

        # Add audio settings if provided
        if inputs.audio_setting is not None:
            arguments["audio_setting"] = {
                "format": inputs.audio_setting.format,
                "sample_rate": inputs.audio_setting.sample_rate,
                "bitrate": inputs.audio_setting.bitrate,
            }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/minimax-music/v2",
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

        # Extract audio from result
        # fal.ai returns: {"audio": {"url": "...", "content_type": "...", "file_size": ...}}
        audio_data = result.get("audio")
        if not audio_data:
            raise ValueError("No audio returned from fal.ai API")

        audio_url = audio_data.get("url")
        if not audio_url:
            raise ValueError("Audio missing URL in fal.ai response")

        # Determine format from audio_setting or content_type
        audio_format = (
            inputs.audio_setting.format if inputs.audio_setting else "mp3"  # Default format
        )

        # Store audio result
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format=audio_format,
            sample_rate=inputs.audio_setting.sample_rate if inputs.audio_setting else 44100,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: MinimaxMusicV2Input) -> float:
        """Estimate cost for minimax-music/v2 generation.

        Estimated at approximately $0.08 per music generation based on typical
        music generation pricing. Actual cost may vary.
        """
        return 0.08  # $0.08 per music generation
