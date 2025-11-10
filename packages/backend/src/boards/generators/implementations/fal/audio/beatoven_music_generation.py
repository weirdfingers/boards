"""
Beatoven music generation - royalty-free instrumental music generator.

Generate high-quality instrumental music from electronic, hip hop, and indie rock
to cinematic and classical genres. Designed for games, films, social content,
podcasts, and similar applications.

Based on Fal AI's beatoven/music-generation model.
See: https://fal.ai/models/beatoven/music-generation
"""

import os

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class BeatovenMusicGenerationInput(BaseModel):
    """Input schema for beatoven music generation.

    All fields use appropriate types and validation based on the Fal AI API.
    """

    prompt: str = Field(
        description="Text description of the desired music (style, mood, instruments, tempo, etc.)"
    )
    duration: float = Field(
        default=90,
        ge=5,
        le=150,
        description="Duration of generated music in seconds (5-150)",
    )
    refinement: int = Field(
        default=100,
        ge=10,
        le=200,
        description="Quality improvement level (10-200, higher is better quality)",
    )
    creativity: float = Field(
        default=16,
        ge=1,
        le=20,
        description="Creative interpretation degree (1-20, higher is more creative)",
    )
    seed: int | None = Field(
        default=None,
        ge=0,
        le=2147483647,
        description="Seed for reproducible results (0-2147483647, null for random)",
    )
    negative_prompt: str = Field(
        default="",
        description="Elements to exclude from the generated music",
    )


class FalBeatovenMusicGenerationGenerator(BaseGenerator):
    """Beatoven music generation using fal.ai."""

    name = "beatoven-music-generation"
    artifact_type = "audio"
    description = "Fal: Beatoven - generate royalty-free instrumental music from text prompts"

    def get_input_schema(self) -> type[BeatovenMusicGenerationInput]:
        return BeatovenMusicGenerationInput

    async def generate(
        self, inputs: BeatovenMusicGenerationInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate music using fal.ai beatoven/music-generation model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBeatovenMusicGenerationGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        from typing import Any

        arguments: dict[str, Any] = {
            "prompt": inputs.prompt,
            "duration": inputs.duration,
            "refinement": inputs.refinement,
            "creativity": inputs.creativity,
        }

        # Add optional parameters if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        if inputs.negative_prompt:
            arguments["negative_prompt"] = inputs.negative_prompt

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "beatoven/music-generation",
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

        # Beatoven returns WAV format
        audio_format = "wav"

        # Store audio result
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format=audio_format,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: BeatovenMusicGenerationInput) -> float:
        """Estimate cost for beatoven music generation.

        Estimated at approximately $0.05 per music generation.
        Actual cost may vary based on duration and quality settings.
        """
        return 0.05  # $0.05 per music generation
