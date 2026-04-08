"""
Kie.ai Suno V5.5 music generation generator.

Generate original music compositions with vocals and lyrics using Suno V5.5,
the latest model with greater control over style, vocals, and creative output.

Based on Kie.ai's Suno API.
See: https://docs.kie.ai/suno-api/generate-music
"""

import asyncio
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from boards.progress.models import ProgressUpdate

from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieBaseGenerator


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


class KieSunoV55Generator(KieBaseGenerator):
    """Suno V5.5 music generator using Kie.ai Suno API.

    Uses the Suno-specific API endpoints:
    - Submit: POST /api/v1/generate
    - Status: GET /api/v1/generate/record-info?taskId={id}
    """

    name = "kie-suno-v5-5"
    artifact_type = "audio"
    description = "Kie.ai: Suno V5.5 - Expressive AI music generation with vocals and lyrics"

    # Not market or dedicated - Suno has its own API pattern
    api_pattern = "dedicated"
    model_id = "suno"

    async def generate(
        self, inputs: SunoV55Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate music using Kie.ai Suno V5.5 model."""
        api_key = self._get_api_key()

        # Prepare request body per Suno API docs
        # callBackUrl is required by the API even when polling;
        # use a placeholder URL that will receive but not process callbacks
        body: dict[str, Any] = {
            "model": "V5_5",
            "customMode": True,
            "title": inputs.title,
            "style": inputs.style,
            "instrumental": inputs.instrumental,
            "callBackUrl": "https://example.com/callback",
        }

        # Only include lyrics for non-instrumental tracks
        if inputs.lyrics and not inputs.instrumental:
            body["prompt"] = inputs.lyrics
        else:
            body["prompt"] = inputs.style

        if inputs.vocal_gender is not None:
            body["vocalGender"] = inputs.vocal_gender

        if inputs.persona_id is not None:
            body["personaId"] = inputs.persona_id

        # Submit task to Suno API endpoint
        submit_url = "https://api.kie.ai/api/v1/generate"
        result = await self._make_request(submit_url, "POST", api_key, json=body)

        # Extract task ID from response
        data = result.get("data", {})
        task_id = data.get("taskId")

        if not task_id:
            # Fallback: check top-level taskId
            task_id = result.get("taskId")

        if not task_id:
            raise ValueError(f"No taskId returned from Kie.ai API. Response: {result}")

        # Store external job ID
        await context.set_external_job_id(task_id)

        # Poll for completion using Suno-specific status endpoint
        result_data = await self._poll_for_completion(task_id, api_key, context)

        # Extract audio URLs from Suno response
        # Response structure: data.response.sunoData[].audioUrl
        response_data = result_data.get("response", {})
        suno_data = response_data.get("sunoData", [])

        if not suno_data:
            raise ValueError(f"No sunoData in response. Response: {result_data}")

        # Store each audio output
        artifacts = []
        for idx, track in enumerate(suno_data):
            audio_url = track.get("audioUrl")
            if not audio_url:
                raise ValueError(f"Track {idx} missing audioUrl in Kie.ai response")

            artifact = await context.store_audio_result(
                storage_url=audio_url,
                format="mp3",
                sample_rate=44100,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def _poll_for_completion(
        self,
        task_id: str,
        api_key: str,
        context: GeneratorExecutionContext,
        max_polls: int = 180,
        poll_interval: int = 10,
    ) -> dict[str, Any]:
        """Poll Suno API for task completion.

        Suno uses its own status endpoint and status field values:
        - "PENDING": Task is queued
        - "TEXT_SUCCESS": Lyrics processed
        - "FIRST_SUCCESS": First track ready
        - "SUCCESS": All tracks complete

        Args:
            task_id: The task ID to poll
            api_key: API key for authorization
            context: Generator execution context for progress updates
            max_polls: Maximum number of polling attempts (default: 180 = 30 minutes)
            poll_interval: Seconds between polls (default: 10)

        Returns:
            The completed task data from the "data" field

        Raises:
            ValueError: If task fails or times out
        """
        status_url = f"https://api.kie.ai/api/v1/generate/record-info?taskId={task_id}"

        async with httpx.AsyncClient() as client:
            for poll_count in range(max_polls):
                # Don't sleep on first poll
                if poll_count > 0:
                    await asyncio.sleep(poll_interval)

                status_response = await client.get(
                    status_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30.0,
                )

                if status_response.status_code != 200:
                    raise ValueError(
                        f"Status check failed: {status_response.status_code} {status_response.text}"
                    )

                status_result = status_response.json()
                self._validate_response(status_result)

                task_data = status_result.get("data", {})
                status = task_data.get("status")

                if status == "SUCCESS":
                    return task_data
                elif status and "FAIL" in status.upper():
                    error_msg = task_data.get("errorMsg", "Unknown error")
                    raise ValueError(f"Generation failed: {error_msg}")

                # Publish progress
                progress = min(90, (poll_count / max_polls) * 100)
                await context.publish_progress(
                    ProgressUpdate(
                        job_id=task_id,
                        status="processing",
                        progress=progress,
                        phase="processing",
                    )
                )
            else:
                timeout_minutes = (max_polls * poll_interval) / 60
                raise ValueError(f"Generation timed out after {timeout_minutes} minutes")

    def get_input_schema(self) -> type[SunoV55Input]:
        return SunoV55Input

    async def estimate_cost(self, inputs: SunoV55Input) -> float:
        """Estimate cost for Suno V5.5 music generation.

        Suno V5.5 costs 12 credits per generation at $0.005/credit = $0.06.
        """
        return 0.06
