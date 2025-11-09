"""
Google Imagen 4 fast text-to-image generator.

Google's highest quality image generation model with support for multiple aspect ratios
and batch generation.

Based on Fal AI's fal-ai/imagen4/preview/fast model.
See: https://fal.ai/models/fal-ai/imagen4/preview/fast
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Imagen4PreviewFastInput(BaseModel):
    """Input schema for Google Imagen 4 fast image generation.

    All parameters are simple types - no artifact inputs needed.
    """

    prompt: str = Field(description="The text prompt describing what you want to see")
    negative_prompt: str = Field(
        default="",
        description="Discourage specific elements in generated images",
    )
    aspect_ratio: Literal["1:1", "16:9", "9:16", "3:4", "4:3"] = Field(
        default="1:1",
        description="Image aspect ratio",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (1-4)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible generation (optional)",
    )


class FalImagen4PreviewFastGenerator(BaseGenerator):
    """Google Imagen 4 fast image generator using fal.ai."""

    name = "fal-imagen4-preview-fast"
    artifact_type = "image"
    description = "Fal: Google Imagen 4 - highest quality text-to-image generation"

    def get_input_schema(self) -> type[Imagen4PreviewFastInput]:
        return Imagen4PreviewFastInput

    async def generate(
        self, inputs: Imagen4PreviewFastInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using Google Imagen 4 via fal.ai."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalImagen4PreviewFastGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "negative_prompt": inputs.negative_prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "num_images": inputs.num_images,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/imagen4/preview/fast",
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
        # fal.ai returns: {"images": [{"url": "...", "content_type": "...", ...}, ...], "seed": ...}
        images = result.get("images", [])
        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Imagen 4 returns PNG images
            # We don't have width/height in the response, so use defaults based on aspect ratio
            # This is a simplification - actual dimensions may vary
            width, height = self._get_dimensions_for_aspect_ratio(inputs.aspect_ratio)

            # Store with appropriate output_index
            artifact = await context.store_image_result(
                storage_url=image_url,
                format="png",
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    def _get_dimensions_for_aspect_ratio(self, aspect_ratio: str) -> tuple[int, int]:
        """Get approximate dimensions for a given aspect ratio.

        Returns (width, height) tuple. Uses 1024 as base for 1:1 ratio.
        """
        aspect_map = {
            "1:1": (1024, 1024),
            "16:9": (1360, 768),
            "9:16": (768, 1360),
            "3:4": (896, 1152),
            "4:3": (1152, 896),
        }
        return aspect_map.get(aspect_ratio, (1024, 1024))

    async def estimate_cost(self, inputs: Imagen4PreviewFastInput) -> float:
        """Estimate cost for Google Imagen 4 generation.

        Pricing information was not available in the documentation.
        Using estimated cost of $0.04 per image based on similar high-quality models.
        """
        # Estimated cost per image (actual pricing may vary)
        cost_per_image = 0.04
        return cost_per_image * inputs.num_images
