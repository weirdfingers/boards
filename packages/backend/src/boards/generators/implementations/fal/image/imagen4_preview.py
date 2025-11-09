"""
fal.ai Imagen 4 Preview text-to-image generator.

Google's highest quality image generation model with support for multiple aspect ratios
and resolutions.
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Imagen4PreviewInput(BaseModel):
    """Input schema for Imagen 4 Preview image generation."""

    prompt: str = Field(description="Text description of desired image")
    aspect_ratio: Literal["1:1", "16:9", "9:16", "3:4", "4:3"] = Field(
        default="1:1",
        description="Image aspect ratio",
    )
    resolution: Literal["1K", "2K"] = Field(
        default="1K",
        description="Image resolution (1K or 2K)",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (max 4)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    negative_prompt: str = Field(
        default="",
        description="Content to exclude from generation",
    )


class FalImagen4PreviewGenerator(BaseGenerator):
    """Imagen 4 Preview image generator using fal.ai."""

    name = "fal-imagen4-preview"
    artifact_type = "image"
    description = "Fal: Imagen 4 - Google's highest quality text-to-image generation model"

    def get_input_schema(self) -> type[Imagen4PreviewInput]:
        return Imagen4PreviewInput

    def _calculate_dimensions(self, aspect_ratio: str, resolution: str) -> tuple[int, int]:
        """Calculate image dimensions based on aspect ratio and resolution.

        Args:
            aspect_ratio: Image aspect ratio (e.g., "16:9")
            resolution: Image resolution ("1K" or "2K")

        Returns:
            Tuple of (width, height)
        """
        # Base size for each resolution
        base_size = 1024 if resolution == "1K" else 2048

        # Dimension mapping for each aspect ratio
        dimensions = {
            "1:1": (base_size, base_size),
            "16:9": (base_size, int(base_size * 9 / 16)),
            "9:16": (int(base_size * 9 / 16), base_size),
            "4:3": (base_size, int(base_size * 3 / 4)),
            "3:4": (int(base_size * 3 / 4), base_size),
        }

        return dimensions.get(aspect_ratio, (base_size, base_size))

    async def generate(
        self, inputs: Imagen4PreviewInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai Imagen 4 Preview model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalImagen4PreviewGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "num_images": inputs.num_images,
            "negative_prompt": inputs.negative_prompt,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/imagen4/preview",
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
        # fal.ai returns: {"images": [{"url": "...", "content_type": "...", ...}, ...]}
        images = result.get("images", [])
        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Calculate dimensions based on inputs
        width, height = self._calculate_dimensions(inputs.aspect_ratio, inputs.resolution)

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Detect format from content_type or URL
            content_type = image_data.get("content_type", "")
            if "png" in content_type.lower():
                format = "png"
            else:
                format = "jpeg"

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

    async def estimate_cost(self, inputs: Imagen4PreviewInput) -> float:
        """Estimate cost for Imagen 4 Preview generation.

        Imagen 4 Preview costs $0.04 per image.
        """
        cost_per_image = 0.04
        return cost_per_image * inputs.num_images
