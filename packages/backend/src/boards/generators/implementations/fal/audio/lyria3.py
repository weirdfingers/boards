"""
fal.ai Google Lyria 3 text-to-music generator.

Generate original music compositions from text descriptions using Google's
Lyria 3 model. Produces 30-second MP3 clips at 44.1kHz / 192kbps with
support for vocals, lyrics, and multi-language output.

Based on Fal AI's fal-ai/lyria3 model.
See: https://fal.ai/models/fal-ai/lyria3
"""

import os

from pydantic import BaseModel, Field

from .....generators.artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Lyria3Input(BaseModel):
    """Input schema for Lyria 3 music generation.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description=(
            "The text prompt describing the music you want to generate. "
            "Include genre, mood, instrumentation, tempo, and vocal style for best results."
        ),
        min_length=1,
        max_length=5000,
    )
    negative_prompt: str = Field(
        default="",
        description="A description of what to exclude from the generated audio.",
    )
    image_url: ImageArtifact | None = Field(
        default=None,
        description=(
            "Optional image to use as inspiration for music generation. "
            "The model will create music that matches the mood and theme of the image."
        ),
    )


class FalLyria3Generator(BaseGenerator):
    """Google Lyria 3 text-to-music generator using fal.ai."""

    name = "fal-lyria3"
    artifact_type = "audio"
    description = (
        "Fal: Google Lyria 3 - "
        "Generate original music compositions from text descriptions with vocals and lyrics"
    )

    def get_input_schema(self) -> type[Lyria3Input]:
        return Lyria3Input

    async def generate(
        self, inputs: Lyria3Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate music using fal.ai Lyria 3 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalLyria3Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict[str, object] = {
            "prompt": inputs.prompt,
        }

        # Only include negative_prompt if non-empty
        if inputs.negative_prompt:
            arguments["negative_prompt"] = inputs.negative_prompt

        # Upload image artifact if provided
        if inputs.image_url is not None:
            from ..utils import upload_artifacts_to_fal

            image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
            arguments["image_url"] = image_urls[0]

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/lyria3",
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
                                progress=50.0,
                                phase="processing",
                                message=message,
                            )
                        )

        # Get final result
        result = await handler.get()

        # Extract audio from result
        # fal.ai returns: {"audio": {"url": "...", "content_type": "...", ...}, "lyrics": "..."}
        audio_data = result.get("audio")
        if not audio_data:
            raise ValueError("No audio data returned from fal.ai API")

        audio_url = audio_data.get("url")
        if not audio_url:
            raise ValueError("Audio URL missing in fal.ai response")

        # Store audio result (Lyria 3 outputs MP3 at 44.1kHz)
        artifact = await context.store_audio_result(
            storage_url=audio_url,
            format="mp3",
            sample_rate=44100,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: Lyria3Input) -> float:
        """Estimate cost for Lyria 3 generation.

        Based on Fal.ai pricing: $0.04 per audio generation.
        """
        return 0.04
