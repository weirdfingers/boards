"""
Kie.ai Veo 3.1 text-to-video and image-to-video generator.

Generate high-quality videos from text prompts with optional image inputs
using Kie.ai's Google Veo 3.1 model (Dedicated API).

Based on Kie.ai's Veo 3.1 API.
See: https://docs.kie.ai/veo3-api/generate-veo-3-video
"""

import asyncio
import os
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from .....progress.models import ProgressUpdate
from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KieVeo3Input(BaseModel):
    """Input schema for Kie.ai Veo 3.1 video generation.

    Supports both text-to-video and image-to-video modes.
    Artifact fields (like image_sources) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="The text prompt describing the video you want to generate",
        max_length=5000,
    )
    image_sources: list[ImageArtifact] | None = Field(
        default=None,
        description="Optional list of 1-2 input images for image-to-video generation",
        min_length=1,
        max_length=2,
    )
    aspect_ratio: Literal["16:9", "9:16", "Auto"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    model: Literal["veo3", "veo3_fast"] = Field(
        default="veo3",
        description="Model variant to use (veo3 for quality, veo3_fast for speed)",
    )


class KieVeo3Generator(BaseGenerator):
    """Veo 3.1 video generator using Kie.ai Dedicated API."""

    name = "kie-veo3"
    artifact_type = "video"
    description = "Kie.ai: Google Veo 3.1 - High-quality AI video generation"

    # Dedicated API configuration
    api_pattern = "dedicated"
    model_id = "veo3"

    def get_input_schema(self) -> type[KieVeo3Input]:
        return KieVeo3Input

    async def generate(
        self, inputs: KieVeo3Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using Kie.ai Veo 3.1 model."""
        # Check for API key
        api_key = os.getenv("KIE_API_KEY")
        if not api_key:
            raise ValueError("API configuration invalid. Missing KIE_API_KEY environment variable")

        # Prepare request body for Dedicated API
        body: dict[str, Any] = {
            "prompt": inputs.prompt,
            "aspectRatio": inputs.aspect_ratio,
            "model": inputs.model,
        }

        # Upload image artifacts if provided (for image-to-video mode)
        if inputs.image_sources:
            from ..utils import upload_artifacts_to_kie

            image_urls = await upload_artifacts_to_kie(inputs.image_sources, context)
            body["imageUrls"] = image_urls

        # Submit task to Dedicated API endpoint
        submit_url = "https://api.kie.ai/api/v1/veo/generate"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                submit_url,
                json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                raise ValueError(
                    f"Kie.ai API request failed: {response.status_code} {response.text}"
                )

            result = response.json()

            # Check for error response
            # Dedicated API uses same structure as Market API: { code, msg, data }
            if result.get("code") != 200:
                error_msg = result.get("msg", "Unknown error")
                raise ValueError(f"Kie.ai API error: {error_msg}")

            # Extract task ID from Dedicated API response
            # Try direct taskId first, then nested under 'data'
            task_id = result.get("taskId")
            if not task_id:
                data = result.get("data", {})
                task_id = data.get("taskId")

            if not task_id:
                raise ValueError(f"No taskId returned from Kie.ai API. Response: {result}")

        # Store external job ID
        await context.set_external_job_id(task_id)

        # Poll for completion using Dedicated API status endpoint
        status_url = f"https://api.kie.ai/api/v1/veo/record-info?taskId={task_id}"

        max_polls = 180  # Maximum number of polls (30 minutes at 10s intervals)
        poll_interval = 10  # Seconds between polls

        result_data = None

        async with httpx.AsyncClient() as client:
            for poll_count in range(max_polls):
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

                if status_result.get("code") != 200:
                    raise ValueError(f"Status check error: {status_result.get('msg')}")

                # Parse Dedicated API status response
                task_data = status_result.get("data", {})
                success_flag = task_data.get("successFlag")

                if success_flag == 1:
                    # Success - extract result
                    result_data = task_data
                    break
                elif success_flag in [2, 3]:
                    # Failed
                    error_msg = task_data.get("errorMsg", "Unknown error")
                    raise ValueError(f"Generation failed: {error_msg}")
                # Continue polling for successFlag == 0 (processing)

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
                raise ValueError("Generation timed out after 30 minutes")

        if not result_data:
            raise ValueError("No result data returned from Kie.ai API")

        # Extract video URLs from response.resultUrls field
        # Dedicated API nests the results inside a 'response' object
        response_data = result_data.get("response")
        if not response_data:
            raise ValueError(f"No response field in result. Response: {result_data}")

        result_urls = response_data.get("resultUrls")
        if not result_urls or not isinstance(result_urls, list):
            raise ValueError(f"No resultUrls in response. Response: {result_data}")

        # Determine video dimensions based on aspect ratio
        # Default to 1080p quality
        if inputs.aspect_ratio == "16:9":
            width, height = 1920, 1080
        elif inputs.aspect_ratio == "9:16":
            width, height = 1080, 1920
        else:  # Auto
            # Default to 16:9 for Auto
            width, height = 1920, 1080

        # Veo 3 generates ~8 second videos by default
        duration = 8.0

        # Store each video using output_index
        artifacts = []
        for idx, video_url in enumerate(result_urls):
            artifact = await context.store_video_result(
                storage_url=video_url,
                format="mp4",
                width=width,
                height=height,
                duration=duration,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: KieVeo3Input) -> float:
        """Estimate cost for Veo 3.1 video generation.

        Veo 3.1 pricing is estimated based on typical video generation costs.
        Actual pricing should be verified at https://kie.ai/pricing

        Base cost estimates:
        - veo3: $0.08 per video (standard quality)
        - veo3_fast: $0.04 per video (faster generation)
        """
        # Cost varies by model
        if inputs.model == "veo3_fast":
            return 0.04
        else:  # veo3
            return 0.08
