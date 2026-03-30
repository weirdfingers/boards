"""
Kie.ai Suno V5.5 music generation generator.

Generate original music compositions with vocals and lyrics using Suno V5.5,
the latest model with greater control over style, vocals, and creative output.

Based on Kie.ai's Suno API (Dedicated API).
See: https://kie.ai/suno-api
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieDedicatedAPIGenerator


class SunoV55Input(BaseModel):
    """Input schema for Suno V5.5 music generation.

    Generate music with lyrics, style descriptions, and vocal control.
    Supports both vocal and instrumental tracks.
    """

    title: str = Field(
        description="The title of the song to generate",
        max_length=200,
    )
    style: str = Field(
        description=(
            "Music style description including genre, mood, instrumentation, "
            "and tempo. E.g. 'upbeat pop with synth bass and acoustic guitar'"
        ),
        max_length=1000,
    )
    lyrics: str = Field(
        default="",
        description=(
            "Song lyrics. Leave empty for instrumental tracks or when "
            "instrumental=True. Supports structured lyrics with sections."
        ),
        max_length=5000,
    )
    instrumental: bool = Field(
        default=False,
        description="Generate instrumental-only track without vocals",
    )
    vocal_gender: Literal["m", "f"] | None = Field(
        default=None,
        description=(
            "Vocal gender preference: 'm' for male, 'f' for female. "
            "Only applies when instrumental is False."
        ),
    )
    persona_id: str | None = Field(
        default=None,
        description=(
            "Optional persona ID for personalized voice/style. "
            "Create personas via the Kie.ai dashboard."
        ),
    )


class KieSunoV55Generator(KieDedicatedAPIGenerator):
    """Suno V5.5 music generator using Kie.ai Dedicated API."""

    name = "kie-suno-v5-5"
    artifact_type = "audio"
    description = "Kie.ai: Suno V5.5 - Expressive AI music generation with vocals and lyrics"

    # Dedicated API configuration
    model_id = "suno"

    def get_input_schema(self) -> type[SunoV55Input]:
        return SunoV55Input

    def _get_status_url(self, task_id: str) -> str:
        """Get the Suno-specific status check URL."""
        return f"https://api.kie.ai/api/v1/suno/record-info?taskId={task_id}"

    async def generate(
        self, inputs: SunoV55Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate music using Kie.ai Suno V5.5 model."""
        api_key = self._get_api_key()

        # Prepare request body for Dedicated API
        body: dict[str, Any] = {
            "model": "V5_5",
            "title": inputs.title,
            "style": inputs.style,
            "lyrics": inputs.lyrics,
            "instrumental": inputs.instrumental,
        }

        if inputs.vocal_gender is not None:
            body["vocalGender"] = inputs.vocal_gender

        if inputs.persona_id is not None:
            body["personaId"] = inputs.persona_id

        # Submit task to Dedicated API endpoint
        submit_url = "https://api.kie.ai/api/v1/suno/generate"
        result = await self._make_request(submit_url, "POST", api_key, json=body)

        # Extract task ID from response
        task_id = result.get("taskId")
        if not task_id:
            data = result.get("data", {})
            task_id = data.get("taskId")

        if not task_id:
            raise ValueError(f"No taskId returned from Kie.ai API. Response: {result}")

        # Store external job ID
        await context.set_external_job_id(task_id)

        # Poll for completion using base class method
        result_data = await self._poll_for_completion(task_id, api_key, context)

        # Extract audio URLs from response
        response_data = result_data.get("response")
        if not response_data:
            response_data = result_data

        # Suno API returns audio URLs in resultUrls or audioUrl fields
        result_urls = response_data.get("resultUrls")
        if not result_urls:
            audio_url = response_data.get("audioUrl")
            if audio_url:
                result_urls = [audio_url]

        if not result_urls or not isinstance(result_urls, list):
            raise ValueError(f"No audio URLs in response. Response: {result_data}")

        # Store each audio output
        artifacts = []
        for idx, audio_url in enumerate(result_urls):
            if not audio_url:
                raise ValueError(f"Audio {idx} missing URL in Kie.ai response")

            artifact = await context.store_audio_result(
                storage_url=audio_url,
                format="mp3",
                sample_rate=44100,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: SunoV55Input) -> float:
        """Estimate cost for Suno V5.5 music generation.

        Suno V5.5 costs 12 credits per generation at $0.005/credit = $0.06.
        """
        return 0.06
