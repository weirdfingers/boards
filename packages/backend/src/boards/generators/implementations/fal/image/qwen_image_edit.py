"""
fal.ai Qwen image editing generator.

An image editing model specializing in text editing within images.
Based on Fal AI's qwen-image-edit model.
See: https://fal.ai/models/fal-ai/qwen-image-edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ImageSize(BaseModel):
    """Custom image size with explicit width and height."""

    width: int = Field(default=512, ge=1, le=14142, description="Image width in pixels")
    height: int = Field(default=512, ge=1, le=14142, description="Image height in pixels")


class QwenImageEditInput(BaseModel):
    """Input schema for Qwen image editing.

    Artifact fields (like image_url) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(description="Text guidance for image editing")
    image_url: ImageArtifact = Field(description="Source image to be edited")
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
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
            "custom dimensions with width/height"
        ),
    )
    acceleration: Literal["none", "regular", "high"] = Field(
        default="regular",
        description="Speed optimization level",
    )
    output_format: Literal["jpeg", "png"] = Field(
        default="png",
        description="Output image format",
    )
    guidance_scale: float = Field(
        default=4.0,
        ge=0.0,
        le=20.0,
        description="CFG intensity controlling prompt adherence (0-20)",
    )
    num_inference_steps: int = Field(
        default=30,
        ge=2,
        le=50,
        description="Number of processing iterations for quality",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    negative_prompt: str = Field(
        default=" ",
        description="Undesired characteristics to avoid in the edited image",
    )
    sync_mode: bool = Field(
        default=False,
        description=(
            "If True, returns data URI instead of stored media "
            "(output won't be available in request history)"
        ),
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable NSFW content filtering",
    )


class FalQwenImageEditGenerator(BaseGenerator):
    """Qwen image editing generator using fal.ai."""

    name = "fal-qwen-image-edit"
    artifact_type = "image"
    description = "Fal: Qwen Image Edit - AI-powered image editing with text editing capabilities"

    def get_input_schema(self) -> type[QwenImageEditInput]:
        return QwenImageEditInput

    async def generate(
        self, inputs: QwenImageEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using fal.ai qwen-image-edit model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalQwenImageEditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        image_url = image_urls[0]

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": image_url,
            "num_images": inputs.num_images,
            "acceleration": inputs.acceleration,
            "output_format": inputs.output_format,
            "guidance_scale": inputs.guidance_scale,
            "num_inference_steps": inputs.num_inference_steps,
            "negative_prompt": inputs.negative_prompt,
            "sync_mode": inputs.sync_mode,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Add optional fields if provided
        if inputs.image_size is not None:
            # If ImageSize object, convert to dict; otherwise use string directly
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
            "fal-ai/qwen-image-edit",
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
        # fal.ai returns: {
        #   "images": [{"url": "...", "width": ..., "height": ..., "content_type": "..."}, ...],
        #   "prompt": "...",
        #   "seed": ...,
        #   "has_nsfw_concepts": [...]
        # }
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url_result = image_data.get("url")
            # Extract dimensions from the response
            width = image_data.get("width", 1024)
            height = image_data.get("height", 1024)

            if not image_url_result:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Store with appropriate output_index
            artifact = await context.store_image_result(
                storage_url=image_url_result,
                format=inputs.output_format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: QwenImageEditInput) -> float:
        """Estimate cost for Qwen image edit generation.

        Based on typical Fal image editing model pricing.
        Using $0.05 per image as a reasonable estimate.
        """
        per_image_cost = 0.05
        return per_image_cost * inputs.num_images
