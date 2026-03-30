"""
Kie.ai Suno Sounds generator for custom audio and sound effects.

Generate audio and sound effects from text prompts with loop playback
and adjustable tempo/key using Kie.ai's Suno Sounds model (Dedicated API).

See: https://docs.kie.ai/suno-api/generate-sounds
"""

import asyncio
import json
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from .....progress.models import ProgressUpdate
from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieDedicatedAPIGenerator

# All valid sound key values
SoundKey = Literal[
    "Any",
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
    "Cm",
    "C#m",
    "Dm",
    "D#m",
    "Em",
    "Fm",
    "F#m",
    "Gm",
    "G#m",
    "Am",
    "A#m",
    "Bm",
]

# Task statuses indicating the task is still in progress
_PROCESSING_STATUSES = {"PENDING", "TEXT_SUCCESS", "FIRST_SUCCESS"}

# Task statuses indicating failure
_FAILED_STATUSES = {
    "CREATE_TASK_FAILED",
    "GENERATE_AUDIO_FAILED",
    "CALLBACK_EXCEPTION",
    "SENSITIVE_WORD_ERROR",
}


class SunoSoundsInput(BaseModel):
    """Input schema for Kie.ai Suno Sounds generation.

    Generates custom audio and sound effects from text prompts with
    optional loop playback and adjustable tempo/key controls.
    """

    prompt: str = Field(
        description="Description of the sound to generate",
        max_length=500,
    )
    model: Literal["V5", "V5_5"] | None = Field(
        default=None,
        description="Model version to use",
    )
    sound_loop: bool = Field(
        default=False,
        description="Enable looping/cycle playback",
    )
    sound_tempo: int | None = Field(
        default=None,
        description="BPM (beats per minute). Auto if not set.",
        ge=1,
        le=300,
    )
    sound_key: SoundKey = Field(
        default="Any",
        description="Musical key/pitch for the generated sound",
    )
    grab_lyrics: bool = Field(
        default=False,
        description="Capture lyric subtitles for output",
    )


class KieSunoSoundsGenerator(KieDedicatedAPIGenerator):
    """Generator for custom audio and sound effects using Suno Sounds."""

    name = "kie-suno-sounds"
    artifact_type = "audio"
    description = "Kie.ai: Suno Sounds - Custom audio and sound effects from prompts"

    # Dedicated API configuration
    model_id = "ai-music-api/sounds"

    def get_input_schema(self) -> type[SunoSoundsInput]:
        return SunoSoundsInput

    def _get_status_url(self, task_id: str) -> str:
        """Get the Suno Sounds status check URL."""
        return f"https://api.kie.ai/api/v1/generate/record-info?taskId={task_id}"

    async def _poll_for_completion(
        self,
        task_id: str,
        api_key: str,
        context: GeneratorExecutionContext,
        max_polls: int = 180,
        poll_interval: int = 10,
    ) -> dict[str, Any]:
        """Poll Suno Sounds API for task completion using string status values.

        The Suno API uses string-based statuses instead of the standard
        Dedicated API successFlag pattern:
        - Processing: PENDING, TEXT_SUCCESS, FIRST_SUCCESS
        - Success: SUCCESS
        - Failed: CREATE_TASK_FAILED, GENERATE_AUDIO_FAILED, etc.
        """
        status_url = self._get_status_url(task_id)

        async with httpx.AsyncClient() as client:
            for poll_count in range(max_polls):
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
                callback_type = task_data.get("callbackType")

                if status == "SUCCESS" or callback_type == "complete":
                    return task_data
                elif status in _FAILED_STATUSES:
                    error_msg = task_data.get("errorMsg") or task_data.get("failMsg") or status
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

    async def generate(
        self, inputs: SunoSoundsInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate audio using Kie.ai Suno Sounds."""
        api_key = self._get_api_key()

        # Prepare request body
        body: dict[str, Any] = {
            "prompt": inputs.prompt,
            "soundLoop": inputs.sound_loop,
            "soundKey": inputs.sound_key,
            "grabLyrics": inputs.grab_lyrics,
        }

        if inputs.model is not None:
            body["model"] = inputs.model

        if inputs.sound_tempo is not None:
            body["soundTempo"] = inputs.sound_tempo

        # Submit task to Suno Sounds endpoint
        submit_url = "https://api.kie.ai/api/v1/generate/sounds"
        result = await self._make_request(submit_url, "POST", api_key, json=body)

        # Extract task ID
        task_id = result.get("taskId")
        if not task_id:
            data = result.get("data", {})
            task_id = data.get("taskId")

        if not task_id:
            raise ValueError(f"No taskId returned from Kie.ai API. Response: {result}")

        await context.set_external_job_id(task_id)

        # Poll for completion
        result_data = await self._poll_for_completion(task_id, api_key, context)

        # Extract audio items from response
        # Suno returns results in data.data[] array
        audio_items = result_data.get("data")
        if not audio_items:
            # Also try parsing resultJson if present
            result_json = result_data.get("resultJson")
            if result_json and isinstance(result_json, str):
                parsed = json.loads(result_json)
                audio_items = parsed.get("data", [])

        if not audio_items or not isinstance(audio_items, list):
            raise ValueError(f"No audio data returned from Kie.ai API. Response: {result_data}")

        # Store each audio artifact
        artifacts = []
        for idx, item in enumerate(audio_items):
            audio_url = item.get("audio_url")
            if not audio_url:
                continue

            duration = item.get("duration")

            artifact = await context.store_audio_result(
                storage_url=audio_url,
                format="mp3",
                duration=duration,
                output_index=idx,
            )
            artifacts.append(artifact)

        if not artifacts:
            raise ValueError("No audio URLs found in Kie.ai API response")

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: SunoSoundsInput) -> float:
        """Estimate cost for Suno Sounds generation.

        Pricing: 2.5 credits per generation (~$0.0125 USD).
        """
        return 0.0125
