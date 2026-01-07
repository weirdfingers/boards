"""
fal.ai GPT Image 1.5 text-to-image generator.

Generate high-fidelity images using GPT Image 1.5 with strong prompt adherence,
preserving composition, lighting, and fine-grained detail.

Based on Fal AI's fal-ai/gpt-image-1.5 model.
See: https://fal.ai/models/fal-ai/gpt-image-1.5
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class GptImage15Input(BaseModel):
    """Input schema for GPT Image 1.5.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="The prompt for image generation",
        min_length=2,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate",
    )
    image_size: Literal["1024x1024", "1536x1024", "1024x1536"] = Field(
        default="1024x1024",
        description="Aspect ratio for the generated image",
    )
    background: Literal["auto", "transparent", "opaque"] = Field(
        default="auto",
        description="Background for the generated image",
    )
    quality: Literal["low", "medium", "high"] = Field(
        default="high",
        description="Quality for the generated image",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output format for the images",
    )


class FalGptImage15Generator(BaseGenerator):
    """GPT Image 1.5 text-to-image generator using fal.ai."""

    name = "fal-gpt-image-1-5"
    artifact_type = "image"
    description = "Fal: GPT Image 1.5 - High-fidelity image generation with strong prompt adherence"

    def get_input_schema(self) -> type[GptImage15Input]:
        return GptImage15Input

    async def generate(
        self, inputs: GptImage15Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai gpt-image-1.5 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGptImage15Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "image_size": inputs.image_size,
            "background": inputs.background,
            "quality": inputs.quality,
            "output_format": inputs.output_format,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/gpt-image-1.5",
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
        #   "images": [{"url": "...", "content_type": "...", "width": ..., "height": ...}, ...]
        # }
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Parse target dimensions from image_size
        size_parts = inputs.image_size.split("x")
        target_width = int(size_parts[0])
        target_height = int(size_parts[1])

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            # Extract dimensions if available, otherwise use target dimensions from input
            width = image_data.get("width") or target_width
            height = image_data.get("height") or target_height

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Store with appropriate output_index
            artifact = await context.store_image_result(
                storage_url=image_url,
                format=inputs.output_format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: GptImage15Input) -> float:
        """Estimate cost for GPT Image 1.5 generation.

        Using estimated cost per image (pricing not documented).
        GPT Image 1.5 is a higher-quality model compared to mini version.
        """
        # Estimated cost per image
        per_image_cost = 0.04
        return per_image_cost * inputs.num_images
