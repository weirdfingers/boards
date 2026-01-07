"""
fal.ai GPT-Image-1.5 image editing generator.

Edit images using OpenAI's GPT-Image-1.5 model via fal.ai.
Based on Fal AI's fal-ai/gpt-image-1.5/edit model.
See: https://fal.ai/models/fal-ai/gpt-image-1.5/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class GptImage15EditInput(BaseModel):
    """Input schema for GPT-Image-1.5 image editing.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="Edit instruction for transforming the input images",
        min_length=2,
        max_length=32000,
    )
    image_urls: list[ImageArtifact] = Field(
        description="URLs of images to use as reference for editing",
        min_length=1,
    )
    mask_image_url: ImageArtifact | None = Field(
        default=None,
        description="Optional mask image to specify the area to edit",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of edited images to generate (1-4)",
    )
    image_size: Literal["auto", "1024x1024", "1536x1024", "1024x1536"] = Field(
        default="auto",
        description="Size of the output images",
    )
    quality: Literal["low", "medium", "high"] = Field(
        default="high",
        description="Quality level of the output images",
    )
    input_fidelity: Literal["low", "high"] = Field(
        default="high",
        description="How closely to follow the input image",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    background: Literal["auto", "transparent", "opaque"] = Field(
        default="auto",
        description="Background handling for the output images",
    )


class FalGptImage15EditGenerator(BaseGenerator):
    """Generator for OpenAI's GPT-Image-1.5 image editing via fal.ai."""

    name = "fal-gpt-image-15-edit"
    description = "Fal: GPT-Image-1.5 Edit - OpenAI's latest image editing model"
    artifact_type = "image"

    def get_input_schema(self) -> type[GptImage15EditInput]:
        """Return the input schema for this generator."""
        return GptImage15EditInput

    async def generate(
        self, inputs: GptImage15EditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate edited images using fal.ai GPT-Image-1.5."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGptImage15EditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal(inputs.image_urls, context)

        # Upload mask image if provided
        mask_image_url = None
        if inputs.mask_image_url is not None:
            mask_urls = await upload_artifacts_to_fal([inputs.mask_image_url], context)
            mask_image_url = mask_urls[0] if mask_urls else None

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "image_urls": image_urls,
            "num_images": inputs.num_images,
            "image_size": inputs.image_size,
            "quality": inputs.quality,
            "input_fidelity": inputs.input_fidelity,
            "output_format": inputs.output_format,
            "background": inputs.background,
        }

        # Add mask image if provided
        if mask_image_url is not None:
            arguments["mask_image_url"] = mask_image_url

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/gpt-image-1.5/edit",
            arguments=arguments,
        )

        # Store external job ID
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates
        from .....progress.models import ProgressUpdate

        event_count = 0
        async for event in handler.iter_events(with_logs=True):
            event_count += 1
            # Sample every 3rd event to avoid spam
            if event_count % 3 == 0:
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
                                progress=50.0,
                                phase="processing",
                                message=message,
                            )
                        )

        # Get final result
        result = await handler.get()

        # Extract images from result
        # Response structure: {"images": [{"url": "...", "width": 1024, "height": 1024, ...}, ...]}
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            width = image_data.get("width", 1024)
            height = image_data.get("height", 1024)

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Determine format from content_type if available, otherwise use input format
            format = inputs.output_format
            if "content_type" in image_data:
                content_type = image_data["content_type"]
                if "jpeg" in content_type:
                    format = "jpeg"
                elif "webp" in content_type:
                    format = "webp"
                elif "png" in content_type:
                    format = "png"

            artifact = await context.store_image_result(
                storage_url=image_url,
                format=format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: GptImage15EditInput) -> float:
        """Estimate cost for GPT-Image-1.5 edit generation.

        Pricing varies by quality and image size:
        - Low Quality: $0.009-$0.013 per image
        - Medium Quality: $0.034-$0.051 per image
        - High Quality: $0.133-$0.200 per image
        """
        # Base costs by quality (using 1024x1024 as reference)
        quality_costs = {
            "low": 0.011,  # Average of $0.009-$0.013
            "medium": 0.045,  # Average of $0.034-$0.051
            "high": 0.177,  # Average of $0.133-$0.200
        }

        per_image_cost = quality_costs.get(inputs.quality, 0.177)
        return per_image_cost * inputs.num_images
