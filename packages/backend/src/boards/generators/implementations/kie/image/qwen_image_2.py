"""
Kie.ai Qwen Image 2.0 generator for image generation and editing.

High-performance image generation and editing with strong text rendering
and native 2K output. Supports both text-to-image and image editing modes
through unified creation + editing workflow.

Based on Kie.ai's Qwen Image 2.0 models (Market API).
- Text-to-Image: qwen2/text-to-image
- Image Edit: qwen2/image-edit
See: https://kie.ai/qwen-image-2
"""

import json
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieMarketAPIGenerator


class QwenImage2Input(BaseModel):
    """Input schema for Qwen Image 2.0 generation and editing.

    When image_sources is provided, uses the image-edit model.
    Otherwise, uses the text-to-image model.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="Text prompt describing the image to generate or the edit to apply",
        max_length=5000,
    )
    image_sources: list[ImageArtifact] | None = Field(
        default=None,
        description=(
            "Optional input images for editing mode"
            " (JPEG, PNG, WEBP; max 10MB each; max 3 images)"
        ),
        min_length=1,
        max_length=3,
    )
    image_size: Literal["1:1", "4:3", "3:4", "16:9", "9:16"] = Field(
        default="1:1",
        description="Output image aspect ratio",
    )
    output_format: Literal["png", "jpeg"] = Field(
        default="png",
        description="Output image format",
    )
    seed: int | None = Field(
        default=None,
        description=(
            "Random seed for reproducibility." " Same seed and prompt produce identical output"
        ),
    )


class KieQwenImage2Generator(KieMarketAPIGenerator):
    """Qwen Image 2.0 generator for image creation and editing using Kie.ai Market API."""

    name = "kie-qwen-image-2"
    artifact_type = "image"
    description = (
        "Kie.ai: Qwen Image 2.0 - High-performance image"
        " generation and editing with text rendering and 2K output"
    )

    # Market API configuration - model_id is set dynamically based on input
    model_id = "qwen2/text-to-image"

    def get_input_schema(self) -> type[QwenImage2Input]:
        return QwenImage2Input

    async def generate(
        self, inputs: QwenImage2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate or edit images using Kie.ai Qwen Image 2.0."""
        api_key = self._get_api_key()

        # Determine which model to use based on input
        is_edit_mode = inputs.image_sources is not None and len(inputs.image_sources) > 0

        if is_edit_mode:
            model_id = "qwen2/image-edit"
        else:
            model_id = "qwen2/text-to-image"

        # Build input parameters
        input_params: dict[str, str | list[str] | int] = {
            "prompt": inputs.prompt,
            "image_size": inputs.image_size,
            "output_format": inputs.output_format,
        }

        if inputs.seed is not None:
            input_params["seed"] = inputs.seed

        # Upload image artifacts if in edit mode
        if is_edit_mode:
            assert inputs.image_sources is not None
            from ..utils import upload_artifacts_to_kie

            image_urls = await upload_artifacts_to_kie(inputs.image_sources, context)
            input_params["image_url"] = image_urls

        # Prepare request body for Market API
        body = {
            "model": model_id,
            "input": input_params,
        }

        # Submit task
        submit_url = "https://api.kie.ai/api/v1/jobs/createTask"
        result = await self._make_request(submit_url, "POST", api_key, json=body)

        data = result.get("data", {})
        task_id = data.get("taskId")

        if not task_id:
            raise ValueError(f"No taskId returned from Kie.ai API. Response: {result}")

        await context.set_external_job_id(task_id)

        # Poll for completion
        task_data = await self._poll_for_completion(task_id, api_key, context)

        # Extract outputs from resultJson
        result_json = task_data.get("resultJson")
        if result_json:
            result_data = json.loads(result_json)
        else:
            result_data = task_data.get("result")

        if not result_data:
            raise ValueError("No result data returned from Kie.ai API")

        # Extract image URLs from result
        images: list[str] = []
        if isinstance(result_data, dict):
            if "resultUrls" in result_data:
                images = result_data["resultUrls"]
            elif "image_urls" in result_data:
                images = result_data["image_urls"]
            elif "url" in result_data:
                images = [result_data["url"]]

        if not images:
            raise ValueError(f"No images found in result: {result_data}")

        # Determine dimensions based on aspect ratio
        aspect_dimensions = {
            "1:1": (2048, 2048),
            "4:3": (2048, 1536),
            "3:4": (1536, 2048),
            "16:9": (2048, 1152),
            "9:16": (1152, 2048),
        }
        width, height = aspect_dimensions.get(inputs.image_size, (2048, 2048))

        artifacts = []
        for idx, image_url in enumerate(images):
            if not image_url:
                raise ValueError(f"Image {idx} missing URL in Kie.ai response")

            artifact = await context.store_image_result(
                storage_url=image_url,
                format=inputs.output_format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: QwenImage2Input) -> float:
        """Estimate cost for Qwen Image 2.0 generation.

        Approximately $0.03 per image based on Kie.ai pricing (~5.6 credits).
        """
        return 0.03
