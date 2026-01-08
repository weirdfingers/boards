"""
Generate high-quality images using ByteDance's Seedream 4.5 text-to-image model.

Based on Fal AI's fal-ai/bytedance/seedream/v4.5/text-to-image model.
See: https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/text-to-image
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class SeedreamV45TextToImageInput(BaseModel):
    """Input schema for Seedream V4.5 text-to-image generation.

    Seedream 4.5 is ByteDance's new-generation image creation model that integrates
    image generation and editing capabilities into a unified architecture.
    """

    prompt: str = Field(description="The text prompt used to generate the image")
    num_images: int = Field(
        default=1,
        ge=1,
        le=6,
        description="Number of images to generate",
    )
    image_size: (
        Literal[
            "square_hd",
            "portrait_4_3",
            "landscape_16_9",
            "auto_2K",
            "auto_4K",
        ]
        | None
    ) = Field(
        default=None,
        description=(
            "The size preset for the generated image. Options include "
            "square_hd, portrait_4_3, landscape_16_9, auto_2K, auto_4K"
        ),
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable or disable the safety checker",
    )


class FalSeedreamV45TextToImageGenerator(BaseGenerator):
    """Generator for high-quality images using ByteDance's Seedream 4.5 model."""

    name = "fal-seedream-v45-text-to-image"
    artifact_type = "image"
    description = "Fal: ByteDance Seedream 4.5 - high-quality text-to-image generation"

    def get_input_schema(self) -> type[SeedreamV45TextToImageInput]:
        """Return the input schema for this generator."""
        return SeedreamV45TextToImageInput

    async def generate(
        self, inputs: SeedreamV45TextToImageInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai ByteDance Seedream 4.5 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalSeedreamV45TextToImageGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict[str, object] = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Add optional parameters
        if inputs.image_size is not None:
            arguments["image_size"] = inputs.image_size

        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/bytedance/seedream/v4.5/text-to-image",
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

        # Extract image data from result
        # fal.ai seedream returns:
        # {"images": [{"url": "...", "width": ..., "height": ..., ...}], "seed": ...}
        images = result.get("images", [])
        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Extract dimensions if available, use defaults otherwise
            width = image_data.get("width", 2048)
            height = image_data.get("height", 2048)

            # Determine format from content_type (e.g., "image/png" -> "png")
            content_type = image_data.get("content_type", "image/png")
            format = content_type.split("/")[-1] if "/" in content_type else "png"

            # Store with appropriate output_index
            artifact = await context.store_image_result(
                storage_url=image_url,
                format=format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: SeedreamV45TextToImageInput) -> float:
        """Estimate cost for Seedream V4.5 generation.

        Seedream V4.5 pricing is approximately $0.03 per image generation.
        Note: Actual pricing may vary. Check Fal AI documentation for current rates.
        """
        return 0.03 * inputs.num_images
