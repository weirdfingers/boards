"""
fal.ai beatoven/sound-effect-generation generator.

Create professional-grade sound effects from animal and vehicle to nature, sci-fi,
and otherworldly sounds. Perfect for films, games, and digital content.

Based on Fal AI's beatoven/sound-effect-generation model.
See: https://fal.ai/models/beatoven/sound-effect-generation
"""

import os

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class BeatovenSoundEffectGenerationInput(BaseModel):
    """Input schema for beatoven/sound-effect-generation.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(description="Describe the sound effect you want to generate")
    duration: float = Field(
        default=5,
        ge=1,
        le=35,
        description="Length of the generated sound effect in seconds",
    )
    refinement: int = Field(
        default=40,
        ge=10,
        le=200,
        description="Refinement level - Higher values may improve quality but take longer",
    )
    creativity: float = Field(
        default=16,
        ge=1,
        le=20,
        description="Creativity level - higher values allow more creative interpretation",
    )
    negative_prompt: str = Field(
        default="",
        description="Describe the types of sounds you don't want to generate",
    )
    seed: int | None = Field(
        default=None,
        ge=0,
        le=2147483647,
        description="Random seed for reproducible results - leave empty for random generation",
    )


class FalBeatovenSoundEffectGenerationGenerator(BaseGenerator):
    """Generator for creating professional-grade sound effects."""

    name = "fal-beatoven-sound-effect-generation"
    description = (
        "Fal: Beatoven Sound Effects - create professional-grade sound effects "
        "for films, games, and digital content"
    )
    artifact_type = "audio"

    def get_input_schema(self) -> type[BeatovenSoundEffectGenerationInput]:
        """Return the input schema for this generator."""
        return BeatovenSoundEffectGenerationInput

    async def generate(
        self, inputs: BeatovenSoundEffectGenerationInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using fal.ai beatoven/sound-effect-generation."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBeatovenSoundEffectGenerationGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        from typing import Any

        arguments: dict[str, Any] = {
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "refinement": inputs.refinement,
            "creativity": inputs.creativity,
            "negative_prompt": inputs.negative_prompt,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job
        handler = await fal_client.submit_async(
            "beatoven/sound-effect-generation",
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

        # Extract audio from result
        # fal.ai returns: {"audio": {"url": "...", "content_type": "...", ...}}
        audio_data = result.get("audio")
        if not audio_data:
            raise ValueError("No audio returned from fal.ai API")

        audio_url = audio_data.get("url")
        if not audio_url:
            raise ValueError("Audio missing URL in fal.ai response")

        # Store audio result (WAV format)
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format="wav",
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: BeatovenSoundEffectGenerationInput) -> float:
        """Estimate cost for this generation in USD.

        Estimated at approximately $0.05 per sound effect generation.
        Actual cost may vary based on duration and refinement settings.
        """
        return 0.05
