"""
Kie.ai Runway Aleph video-to-video generator.

Transform video clips using Runway's Aleph model via Kie.ai's Dedicated API.
Aleph is Runway's 'in-context' video model with multi-task editing capabilities
including adding/removing objects, relighting, changing angles or styles via
text prompts, with advanced scene reasoning and precise camera control.

Based on Kie.ai's Runway Aleph API.
See: https://docs.kie.ai/runway-api/generate-aleph-video
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact, VideoArtifact
from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieDedicatedAPIGenerator


class KieRunwayAlephInput(BaseModel):
    """Input schema for Kie.ai Runway Aleph video generation.

    Video-to-video transformation using Runway's Aleph model.
    Artifact fields (like video_source, reference_image) are automatically
    detected via type introspection and resolved from generation IDs to
    artifact objects.
    """

    prompt: str = Field(
        description="Text prompt describing the desired video transformation",
        max_length=5000,
    )
    video_source: VideoArtifact = Field(
        description="Source video to transform (max 5 seconds will be processed)",
    )
    reference_image: ImageArtifact | None = Field(
        default=None,
        description="Optional reference image to influence output style",
    )
    aspect_ratio: Literal["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"] | None = Field(
        default=None,
        description="Aspect ratio of the generated video (defaults to source video ratio)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible generation",
    )


class KieRunwayAlephGenerator(KieDedicatedAPIGenerator):
    """Runway Aleph video-to-video generator using Kie.ai Dedicated API."""

    name = "kie-runway-aleph"
    artifact_type = "video"
    description = "Kie.ai: Runway Aleph - In-context video editing with multi-task capabilities"

    # Dedicated API configuration
    model_id = "aleph"

    def get_input_schema(self) -> type[KieRunwayAlephInput]:
        return KieRunwayAlephInput

    def _get_status_url(self, task_id: str) -> str:
        """Get the Aleph-specific status check URL."""
        return f"https://api.kie.ai/api/v1/aleph/record-info?taskId={task_id}"

    async def generate(
        self, inputs: KieRunwayAlephInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using Kie.ai Runway Aleph model."""
        api_key = self._get_api_key()

        # Upload video artifact to get a public URL
        from ..utils import upload_artifacts_to_kie

        video_urls = await upload_artifacts_to_kie([inputs.video_source], context)
        video_url = video_urls[0]

        # Prepare request body
        body: dict[str, Any] = {
            "prompt": inputs.prompt,
            "videoUrl": video_url,
        }

        if inputs.aspect_ratio is not None:
            body["aspectRatio"] = inputs.aspect_ratio

        if inputs.seed is not None:
            body["seed"] = inputs.seed

        # Upload and set reference image if provided
        if inputs.reference_image:
            image_urls = await upload_artifacts_to_kie([inputs.reference_image], context)
            body["referenceImage"] = image_urls[0]

        # Submit task
        submit_url = "https://api.kie.ai/api/v1/aleph/generate"
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

        # Extract video URL from response
        response_data = result_data.get("response")
        if not response_data:
            raise ValueError(f"No response field in result. Response: {result_data}")

        result_video_url = response_data.get("resultVideoUrl")
        if not result_video_url:
            raise ValueError(f"No resultVideoUrl in response. Response: {result_data}")

        # Determine dimensions based on aspect ratio or default to source
        width, height = self._get_dimensions(inputs.aspect_ratio)

        # Aleph processes up to 5 seconds of video
        duration = 5.0

        artifact = await context.store_video_result(
            storage_url=result_video_url,
            format="mp4",
            width=width,
            height=height,
            duration=duration,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    def _get_dimensions(self, aspect_ratio: str | None) -> tuple[int, int]:
        """Get video dimensions based on aspect ratio."""
        dimensions = {
            "16:9": (1920, 1080),
            "9:16": (1080, 1920),
            "4:3": (1440, 1080),
            "3:4": (1080, 1440),
            "1:1": (1080, 1080),
            "21:9": (2520, 1080),
        }
        if aspect_ratio and aspect_ratio in dimensions:
            return dimensions[aspect_ratio]
        # Default to 16:9
        return (1920, 1080)

    async def estimate_cost(self, inputs: KieRunwayAlephInput) -> float:
        """Estimate cost for Runway Aleph video generation.

        Pricing estimated based on typical Runway video generation costs.
        Actual pricing should be verified at https://kie.ai/pricing
        """
        return 0.10
