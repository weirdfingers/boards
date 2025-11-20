"""
fal.ai ElevenLabs Text-to-Speech Eleven-V3 generator.

Generate high-quality speech from text using ElevenLabs' Eleven-V3 model,
offering natural-sounding voices with customizable parameters for stability,
similarity, style, and speed.

Based on Fal AI's fal-ai/elevenlabs/tts/eleven-v3 model.
See: https://fal.ai/models/fal-ai/elevenlabs/tts/eleven-v3
"""

import os

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ElevenlabsTtsElevenV3Input(BaseModel):
    """Input schema for ElevenLabs TTS Eleven-V3 generation.

    The text is converted to speech using advanced AI voice synthesis with
    customizable voice characteristics and optional word-level timestamps.
    """

    text: str = Field(
        description="The text to convert to speech",
        min_length=1,
    )
    voice: str = Field(
        default="Rachel",
        description=(
            "Voice selection. Available voices: "
            "Aria, Roger, Sarah, Laura, Charlie, George, Callum, River, Liam, "
            "Charlotte, Alice, Matilda, Will, Jessica, Eric, Chris, Brian, "
            "Daniel, Lily, Bill, Rachel"
        ),
    )
    stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice stability. Higher values result in more consistent output",
    )
    similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Similarity boost for voice matching",
    )
    style: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Style exaggeration. Higher values add more expressiveness",
    )
    speed: float = Field(
        default=1.0,
        ge=0.7,
        le=1.2,
        description="Speech rate adjustment. 1.0 is normal speed",
    )
    timestamps: bool = Field(
        default=False,
        description="Whether to return timestamps for each word",
    )
    previous_text: str | None = Field(
        default=None,
        description="Context from prior content for improved continuity",
    )
    next_text: str | None = Field(
        default=None,
        description="Context for upcoming content for improved continuity",
    )
    language_code: str | None = Field(
        default=None,
        description="ISO 639-1 language code (limited model support)",
    )


class FalElevenlabsTtsElevenV3Generator(BaseGenerator):
    """ElevenLabs Text-to-Speech Eleven-V3 generator using fal.ai."""

    name = "fal-elevenlabs-tts-eleven-v3"
    artifact_type = "audio"
    description = (
        "Fal: ElevenLabs TTS Eleven-V3 - "
        "High-quality text-to-speech with natural-sounding voices and customizable parameters"
    )

    def get_input_schema(self) -> type[ElevenlabsTtsElevenV3Input]:
        return ElevenlabsTtsElevenV3Input

    async def generate(
        self, inputs: ElevenlabsTtsElevenV3Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using fal.ai ElevenLabs TTS Eleven-V3 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalElevenlabsTtsElevenV3Generator. "
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

        # Add optional context parameters if provided
        if inputs.previous_text is not None:
            arguments["previous_text"] = inputs.previous_text
        if inputs.next_text is not None:
            arguments["next_text"] = inputs.next_text
        if inputs.language_code is not None:
            arguments["language_code"] = inputs.language_code

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/elevenlabs/tts/eleven-v3",
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

        # Determine format from content_type or default to mp3
        content_type = audio_data.get("content_type", "audio/mpeg")
        format_map = {
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
            "audio/ogg": "ogg",
        }
        audio_format = format_map.get(content_type, "mp3")

        # Store audio result
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format=audio_format,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: ElevenlabsTtsElevenV3Input) -> float:
        """Estimate cost for ElevenLabs TTS Eleven-V3 generation.

        ElevenLabs TTS Eleven-V3 costs $0.10 per 1000 characters.
        """
        # Calculate character count
        char_count = len(inputs.text)

        # Cost is $0.10 per 1000 characters
        return (char_count / 1000.0) * 0.10
