"""
Google Gemini 2.5 Flash Image text-to-image generator.

Google's state-of-the-art image generation and editing model available through fal.ai.
Supports multiple aspect ratios and output formats with batch generation up to 4 images.

Based on Fal AI's fal-ai/gemini-25-flash-image model.
See: https://fal.ai/models/fal-ai/gemini-25-flash-image
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Gemini25FlashImageInput(BaseModel):
    """Input schema for Gemini 2.5 Flash Image generation."""

    prompt: str = Field(
        description="Text prompt for image generation",
        min_length=3,
        max_length=5000,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (max 4)",
    )
    aspect_ratio: Literal[
        "21:9",
        "16:9",
        "3:2",
        "4:3",
        "5:4",
        "1:1",
        "4:5",
        "3:4",
        "2:3",
        "9:16",
    ] = Field(
        default="1:1",
        description="Image aspect ratio",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    sync_mode: bool = Field(
        default=False,
        description="Return media as data URI without request history storage",
    )
    limit_generations: bool = Field(
        default=False,
        description="Restrict to single generation per round (experimental)",
    )


class FalGemini25FlashImageGenerator(BaseGenerator):
    """Google Gemini 2.5 Flash Image generator using fal.ai."""

    name = "fal-gemini-25-flash-image"
    artifact_type = "image"
    description = "Fal: Gemini 2.5 Flash Image - Google's state-of-the-art text-to-image generation"

    def get_input_schema(self) -> type[Gemini25FlashImageInput]:
        return Gemini25FlashImageInput

    async def generate(
        self, inputs: Gemini25FlashImageInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using Google Gemini 2.5 Flash Image via fal.ai."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGemini25FlashImageGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "aspect_ratio": inputs.aspect_ratio,
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
            "limit_generations": inputs.limit_generations,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/gemini-25-flash-image",
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
        # fal.ai returns: {"images": [{"url": "...", "width": ..., "height": ..., ...}, ...]}
        images = result.get("images", [])
        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
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

    async def estimate_cost(self, inputs: Gemini25FlashImageInput) -> float:
        """Estimate cost for Gemini 2.5 Flash Image generation.

        TODO: Pricing information not available in fal.ai documentation.
        This is a placeholder estimate that should be updated when pricing is known.
        """
        # Placeholder cost estimate per image (to be updated with actual pricing)
        cost_per_image = 0.00  # Unknown pricing
        return cost_per_image * inputs.num_images
