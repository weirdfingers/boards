"""
fal.ai GPT Image 1 Mini text-to-image generator.

Generate images using OpenAI's GPT-5 language capabilities combined with GPT Image 1 Mini
for efficient image generation.

Based on Fal AI's fal-ai/gpt-image-1-mini model.
See: https://fal.ai/models/fal-ai/gpt-image-1-mini
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class GptImage1MiniInput(BaseModel):
    """Input schema for GPT Image 1 Mini.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="Image generation instruction",
        min_length=3,
        max_length=5000,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="jpeg",
        description="Output image format",
    )
    sync_mode: bool = Field(
        default=False,
        description=(
            "If True, the media will be returned as a data URI and the output "
            "data won't be available in the request history"
        ),
    )


class FalGptImage1MiniGenerator(BaseGenerator):
    """GPT Image 1 Mini text-to-image generator using fal.ai."""

    name = "fal-gpt-image-1-mini"
    artifact_type = "image"
    description = "Fal: GPT Image 1 Mini - Efficient text-to-image generation with GPT-5"

    def get_input_schema(self) -> type[GptImage1MiniInput]:
        return GptImage1MiniInput

    async def generate(
        self, inputs: GptImage1MiniInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai gpt-image-1-mini model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGptImage1MiniGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/gpt-image-1-mini",
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

        # Extract image URLs and description from result
        # fal.ai returns: {
        #   "images": [{"url": "...", "content_type": "...", ...}, ...],
        #   "description": "Text description"
        # }
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            # Extract dimensions if available, otherwise use sensible defaults
            # Use 'or' to handle explicit None values from API
            width = image_data.get("width") or 1024
            height = image_data.get("height") or 1024

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

    async def estimate_cost(self, inputs: GptImage1MiniInput) -> float:
        """Estimate cost for GPT Image 1 Mini generation.

        Using estimated cost per image (pricing not documented).
        """
        # Estimated cost per image
        per_image_cost = 0.01
        return per_image_cost * inputs.num_images
