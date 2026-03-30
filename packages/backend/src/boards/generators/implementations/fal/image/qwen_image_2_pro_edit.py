"""
fal.ai Qwen Image 2 Pro edit generator.

Next-generation unified generation-and-editing model with improved quality.
Based on Fal AI's qwen-image-2/pro/edit model.
See: https://fal.ai/models/fal-ai/qwen-image-2/pro/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ImageSize(BaseModel):
    """Custom image size with explicit width and height."""

    width: int = Field(default=512, ge=512, le=2048, description="Image width in pixels")
    height: int = Field(default=512, ge=512, le=2048, description="Image height in pixels")


class QwenImage2ProEditInput(BaseModel):
    """Input schema for Qwen Image 2 Pro editing.

    Artifact fields (like image_urls) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        max_length=800,
        description="Text describing desired edits. Supports Chinese and English.",
    )
    image_urls: list[ImageArtifact] = Field(
        min_length=1,
        max_length=3,
        description="1-3 reference images for editing (384-5000px per dimension, max 10MB each)",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=6,
        description="Number of edited images to generate",
    )
    image_size: (
        Literal[
            "square_hd",
            "square",
            "portrait_4_3",
            "portrait_16_9",
            "landscape_4_3",
            "landscape_16_9",
        ]
        | ImageSize
        | None
    ) = Field(
        default=None,
        description=(
            "Output image dimensions. Can be a preset (e.g., 'square_hd') or "
            "custom dimensions with width/height (512-2048)"
        ),
    )
    negative_prompt: str = Field(
        default="",
        max_length=500,
        description="Content to avoid in the edited image",
    )
    enable_prompt_expansion: bool = Field(
        default=True,
        description="Enable LLM optimization of the prompt",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    seed: int | None = Field(
        default=None,
        ge=0,
        le=2147483647,
        description="Random seed for reproducibility (optional)",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable NSFW content filtering",
    )
    sync_mode: bool = Field(
        default=False,
        description=(
            "If True, returns data URI instead of stored media "
            "(output won't be available in request history)"
        ),
    )


class FalQwenImage2ProEditGenerator(BaseGenerator):
    """Qwen Image 2 Pro edit generator using fal.ai."""

    name = "fal-qwen-image-2-pro-edit"
    artifact_type = "image"
    description = "Fal: Qwen Image 2 Pro Edit - next-gen image editing with improved quality"

    def get_input_schema(self) -> type[QwenImage2ProEditInput]:
        return QwenImage2ProEditInput

    async def generate(
        self, inputs: QwenImage2ProEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using fal.ai qwen-image-2/pro/edit model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalQwenImage2ProEditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal(inputs.image_urls, context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "image_urls": image_urls,
            "num_images": inputs.num_images,
            "negative_prompt": inputs.negative_prompt,
            "enable_prompt_expansion": inputs.enable_prompt_expansion,
            "output_format": inputs.output_format,
            "enable_safety_checker": inputs.enable_safety_checker,
            "sync_mode": inputs.sync_mode,
        }

        # Add optional fields if provided
        if inputs.image_size is not None:
            if isinstance(inputs.image_size, ImageSize):
                arguments["image_size"] = {
                    "width": inputs.image_size.width,
                    "height": inputs.image_size.height,
                }
            else:
                arguments["image_size"] = inputs.image_size

        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/qwen-image-2/pro/edit",
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

        # Extract image URLs from result
        # fal.ai returns: {"images": [{"url": "...", ...}, ...], "seed": ...}
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url_result = image_data.get("url")
            width = image_data.get("width", 1024)
            height = image_data.get("height", 1024)

            if not image_url_result:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            artifact = await context.store_image_result(
                storage_url=image_url_result,
                format=inputs.output_format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: QwenImage2ProEditInput) -> float:
        """Estimate cost for Qwen Image 2 Pro edit generation.

        Based on typical Fal pro model pricing.
        Using $0.06 per image as a reasonable estimate for the pro tier.
        """
        per_image_cost = 0.06
        return per_image_cost * inputs.num_images
