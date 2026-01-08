"""
fal.ai Reve text-to-image generator.

Reve's text-to-image model generates detailed visual output that closely follows
your instructions, with strong aesthetic quality and accurate text rendering.

Based on Fal AI's fal-ai/reve/text-to-image model.
See: https://fal.ai/models/fal-ai/reve/text-to-image
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ReveTextToImageInput(BaseModel):
    """Input schema for Reve text-to-image generation."""

    prompt: str = Field(
        description="Text description of desired image",
        min_length=1,
        max_length=2560,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate",
    )
    aspect_ratio: Literal["16:9", "9:16", "3:2", "2:3", "4:3", "3:4", "1:1"] = Field(
        default="3:2",
        description="Desired image aspect ratio",
    )
    output_format: Literal["png", "jpeg", "webp"] = Field(
        default="png",
        description="Output image format",
    )


class FalReveTextToImageGenerator(BaseGenerator):
    """Reve text-to-image generator using fal.ai."""

    name = "fal-reve-text-to-image"
    artifact_type = "image"
    description = (
        "Fal: Reve - detailed text-to-image with strong aesthetic quality "
        "and accurate text rendering"
    )

    def get_input_schema(self) -> type[ReveTextToImageInput]:
        return ReveTextToImageInput

    async def generate(
        self, inputs: ReveTextToImageInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai Reve text-to-image model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalReveTextToImageGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "aspect_ratio": inputs.aspect_ratio,
            "output_format": inputs.output_format,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/reve/text-to-image",
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
        # fal.ai returns: {"images": [{"url": "...", "width": ..., "height": ...}, ...]}
        images = result.get("images", [])
        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            width = image_data.get("width")
            height = image_data.get("height")

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

    async def estimate_cost(self, inputs: ReveTextToImageInput) -> float:
        """Estimate cost for Reve text-to-image generation.

        Reve typically costs around $0.03 per image.
        """
        return 0.03 * inputs.num_images
