"""
Kie.ai Grok Imagine Extend video extension generator.

Extend previously generated Grok Imagine videos with additional content
using text prompts via Kie.ai's Market API.

Based on Kie.ai's grok-imagine/extend model (Market API).
See: https://kie.ai/grok-imagine?model=grok-imagine%2Fextend
"""

import json
from typing import Literal

from pydantic import BaseModel, Field

from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieMarketAPIGenerator


class GrokImagineExtendInput(BaseModel):
    """Input schema for Grok Imagine Extend video extension.

    Extends a previously generated Grok Imagine video by appending
    new content based on a text prompt. The task_id must reference
    a successfully completed Kie.ai video generation task.
    """

    task_id: str = Field(
        description="Task ID from a previously successful Kie.ai video generation task. "
        "Only Kie AI-generated task IDs are supported.",
        max_length=100,
    )
    prompt: str = Field(
        description="Text prompt describing the desired video motion for the extension. "
        "Supports both English and Chinese.",
        max_length=5000,
    )
    extend_at: str | None = Field(
        default=None,
        description="Starting point of the extension in the original video (e.g. '0')",
    )
    extend_times: Literal["6", "10"] = Field(
        default="6",
        description="Duration of the extended video in seconds: '6' or '10'",
    )


class KieGrokImagineExtendGenerator(KieMarketAPIGenerator):
    """Grok Imagine Extend video generator using Kie.ai Market API."""

    name = "kie-grok-imagine-extend"
    artifact_type = "video"
    description = "Kie.ai: Grok Imagine Extend - Extend AI-generated videos with text prompts"

    # Market API configuration
    model_id = "grok-imagine/extend"

    def get_input_schema(self) -> type[GrokImagineExtendInput]:
        return GrokImagineExtendInput

    async def generate(
        self, inputs: GrokImagineExtendInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Extend a video using Kie.ai Grok Imagine Extend model."""
        # Get API key using base class method
        api_key = self._get_api_key()

        # Prepare request body for Market API
        input_params: dict[str, str] = {
            "task_id": inputs.task_id,
            "prompt": inputs.prompt,
            "extend_times": inputs.extend_times,
        }

        if inputs.extend_at is not None:
            input_params["extend_at"] = inputs.extend_at

        body = {
            "model": self.model_id,
            "input": input_params,
        }

        # Submit task using base class method
        submit_url = "https://api.kie.ai/api/v1/jobs/createTask"
        result = await self._make_request(submit_url, "POST", api_key, json=body)

        # Extract task ID
        data = result.get("data", {})
        task_id = data.get("taskId")

        if not task_id:
            raise ValueError(f"No taskId returned from Kie.ai API. Response: {result}")

        # Store external job ID
        await context.set_external_job_id(task_id)

        # Poll for completion using base class method
        task_data = await self._poll_for_completion(task_id, api_key, context)

        # Extract outputs from resultJson (Market API pattern)
        result_json = task_data.get("resultJson")
        if result_json:
            result_data = json.loads(result_json)
        else:
            result_data = task_data.get("result")

        if not result_data:
            raise ValueError("No result data returned from Kie.ai API")

        # Extract video URLs from result
        video_urls: list[str] = []
        if isinstance(result_data, dict):
            if "resultUrls" in result_data:
                video_urls = result_data["resultUrls"]
            elif "video_urls" in result_data:
                video_urls = result_data["video_urls"]
            elif "url" in result_data:
                video_urls = [result_data["url"]]

        if not video_urls:
            raise ValueError(f"No video URLs found in result: {result_data}")

        # Determine duration from extend_times
        duration = float(inputs.extend_times)

        # Default to 720p dimensions (common for video extensions)
        width = 1280
        height = 720

        # Store each video using output_index
        artifacts = []
        for idx, video_url in enumerate(video_urls):
            if not video_url:
                raise ValueError(f"Video {idx} missing URL in Kie.ai response")

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

    async def estimate_cost(self, inputs: GrokImagineExtendInput) -> float:
        """Estimate cost for Grok Imagine Extend generation.

        Pricing (at $0.005/credit):
        - 6s 480p = 10 credits = $0.05
        - 6s 720p = 20 credits = $0.10
        - 10s 480p = 20 credits = $0.10
        - 10s 720p = 30 credits = $0.15

        Uses 720p pricing as default estimate since resolution
        is not a user-configurable parameter.
        """
        if inputs.extend_times == "10":
            return 0.15  # 30 credits at $0.005/credit (720p)
        else:  # "6"
            return 0.10  # 20 credits at $0.005/credit (720p)
