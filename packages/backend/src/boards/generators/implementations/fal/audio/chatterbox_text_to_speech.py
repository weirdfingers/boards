"""
fal.ai Chatterbox Text-to-Speech generator.

Generate expressive speech from text using Resemble AI's Chatterbox model.
Supports emotive tags for natural expressions like laughing, sighing, and more.

Based on Fal AI's fal-ai/chatterbox/text-to-speech model.
See: https://fal.ai/models/fal-ai/chatterbox/text-to-speech
"""

import os

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ChatterboxTextToSpeechInput(BaseModel):
    """Input schema for Chatterbox text-to-speech generation.

    Supports emotive tags: <laugh>, <chuckle>, <sigh>, <cough>,
    <sniffle>, <groan>, <yawn>, <gasp>
    """

    text: str = Field(
        description=(
            "The text to be converted to speech. You can add emotive tags like "
            "<laugh>, <chuckle>, <sigh>, <cough>, <sniffle>, <groan>, <yawn>, <gasp>"
        ),
        min_length=1,
    )
    audio_url: str | None = Field(
        default=None,
        description=(
            "Reference audio file URL for voice style matching. "
            "If not provided, uses a default voice sample."
        ),
    )
    exaggeration: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Speech exaggeration intensity factor (0.0 to 1.0)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.05,
        le=2.0,
        description="Creativity level for generation (0.05 to 2.0)",
    )
    cfg: float = Field(
        default=0.5,
        ge=0.1,
        le=1.0,
        description="Configuration parameter for generation (0.1 to 1.0)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible audio generation",
    )


class FalChatterboxTextToSpeechGenerator(BaseGenerator):
    """Chatterbox text-to-speech generator using fal.ai.

    Leverages Resemble AI's Chatterbox model to generate expressive speech
    with support for emotive tags and voice cloning via reference audio.
    """

    name = "fal-chatterbox-text-to-speech"
    artifact_type = "audio"
    description = (
        "Fal: Chatterbox TTS - Expressive text-to-speech with emotive tags and voice cloning"
    )

    def get_input_schema(self) -> type[ChatterboxTextToSpeechInput]:
        return ChatterboxTextToSpeechInput

    async def generate(
        self, inputs: ChatterboxTextToSpeechInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using fal.ai Chatterbox text-to-speech model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalChatterboxTextToSpeechGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "text": inputs.text,
            "exaggeration": inputs.exaggeration,
            "temperature": inputs.temperature,
            "cfg": inputs.cfg,
        }

        # Add optional parameters if provided
        if inputs.audio_url is not None:
            arguments["audio_url"] = inputs.audio_url
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/chatterbox/text-to-speech",
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
            format="mp3",  # Chatterbox returns MP3 format
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: ChatterboxTextToSpeechInput) -> float:
        """Estimate cost for Chatterbox text-to-speech generation.

        Chatterbox pricing is approximately $0.03 per generation.
        """
        # Fixed cost per generation
        return 0.03
