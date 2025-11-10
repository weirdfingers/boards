"""
fal.ai GPT-Image-1 image editing generator.

Edit images using OpenAI's GPT-Image-1 model via fal.ai.
Based on Fal AI's fal-ai/gpt-image-1/edit-image model.
See: https://fal.ai/models/fal-ai/gpt-image-1/edit-image
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class GptImage1EditImageInput(BaseModel):
    """Input schema for GPT-Image-1 image editing.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="Edit instruction for transforming the input images",
        min_length=1,
        max_length=32000,
    )
    image_urls: list[ImageArtifact] = Field(
        description="URLs of images to use as reference for editing",
        min_length=1,
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
    input_fidelity: Literal["low", "high"] = Field(
        default="low",
        description="How closely to follow the input image",
    )
    quality: Literal["auto", "low", "medium", "high"] = Field(
        default="auto",
        description="Quality level of the output images",
    )


class FalGptImage1EditImageGenerator(BaseGenerator):
    """Generator for OpenAI's GPT-Image-1 image editing via fal.ai."""

    name = "fal-gpt-image-1-edit-image"
    description = "Fal: GPT-Image-1 Edit - OpenAI's image editing model"
    artifact_type = "image"

    def get_input_schema(self) -> type[GptImage1EditImageInput]:
        """Return the input schema for this generator."""
        return GptImage1EditImageInput

    async def generate(
        self, inputs: GptImage1EditImageInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate edited images using fal.ai GPT-Image-1."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGptImage1EditImageGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal(inputs.image_urls, context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_urls": image_urls,
            "num_images": inputs.num_images,
            "image_size": inputs.image_size,
            "input_fidelity": inputs.input_fidelity,
            "quality": inputs.quality,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/gpt-image-1/edit-image",
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

            # Determine format from image_size or content_type
            format = "png"  # GPT-Image-1 typically returns PNG
            if "content_type" in image_data:
                content_type = image_data["content_type"]
                if "jpeg" in content_type:
                    format = "jpeg"
                elif "webp" in content_type:
                    format = "webp"

            artifact = await context.store_image_result(
                storage_url=image_url,
                format=format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: GptImage1EditImageInput) -> float:
        """Estimate cost for GPT-Image-1 edit generation.

        Note: Pricing information not available in documentation.
        Using estimated cost based on similar OpenAI image models.
        """
        # Estimated cost per image (similar to other image editing models)
        per_image_cost = 0.04
        return per_image_cost * inputs.num_images
