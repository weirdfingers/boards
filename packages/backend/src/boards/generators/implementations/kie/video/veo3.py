"""
Kie.ai Veo 3.1 text-to-video and image-to-video generator.

Generate high-quality videos from text prompts with optional image inputs
using Kie.ai's Google Veo 3.1 model (Dedicated API).

Based on Kie.ai's Veo 3.1 API.
See: https://docs.kie.ai/veo3-api/generate-veo-3-video
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieDedicatedAPIGenerator


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


class KieVeo3Generator(KieDedicatedAPIGenerator):
    """Veo 3.1 video generator using Kie.ai Dedicated API."""

    name = "kie-veo3"
    artifact_type = "video"
    description = "Kie.ai: Google Veo 3.1 - High-quality AI video generation"

    # Dedicated API configuration
    model_id = "veo3"

    def get_input_schema(self) -> type[KieVeo3Input]:
        return KieVeo3Input

    def _get_status_url(self, task_id: str) -> str:
        """Get the Veo3-specific status check URL."""
        return f"https://api.kie.ai/api/v1/veo/record-info?taskId={task_id}"

    async def generate(
        self, inputs: KieVeo3Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using Kie.ai Veo 3.1 model."""
        # Get API key using base class method
        api_key = self._get_api_key()

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

        # Submit task to Dedicated API endpoint using base class method
        submit_url = "https://api.kie.ai/api/v1/veo/generate"
        result = await self._make_request(submit_url, "POST", api_key, json=body)

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

        # Poll for completion using base class method
        result_data = await self._poll_for_completion(task_id, api_key, context)

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
