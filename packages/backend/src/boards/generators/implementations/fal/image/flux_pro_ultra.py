"""
fal.ai FLUX1.1 [pro] ultra text-to-image generator.

High-quality image generation using fal.ai's FLUX1.1 [pro] ultra model with support for
batch outputs and advanced controls.
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class FluxProUltraInput(BaseModel):
    """Input schema for FLUX1.1 [pro] ultra image generation."""

    prompt: str = Field(description="Text prompt for image generation")
    aspect_ratio: Literal[
        "21:9",
        "16:9",
        "4:3",
        "3:2",
        "1:1",
        "2:3",
        "3:4",
        "9:16",
        "9:21",
    ] = Field(
        default="16:9",
        description="Image aspect ratio",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate in batch (max 4)",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter unsafe content",
    )
    safety_tolerance: int = Field(
        default=2,
        ge=1,
        le=6,
        description="Safety tolerance level (1 = most strict, 6 = most permissive)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    output_format: Literal["jpeg", "png"] = Field(
        default="jpeg",
        description="Output image format",
    )
    enhance_prompt: bool = Field(
        default=False,
        description="Whether to enhance the prompt for better results",
    )
    raw: bool = Field(
        default=False,
        description="Generate less processed, more natural-looking images",
    )
    sync_mode: bool = Field(
        default=True,
        description="Use synchronous mode (wait for completion)",
    )


class FalFluxProUltraGenerator(BaseGenerator):
    """FLUX1.1 [pro] ultra image generator using fal.ai."""

    name = "fal-flux-pro-ultra"
    artifact_type = "image"
    description = (
        "Fal: FLUX1.1 [pro] ultra - high-quality text-to-image generation with advanced controls"
    )

    def get_input_schema(self) -> type[FluxProUltraInput]:
        return FluxProUltraInput

    async def generate(
        self, inputs: FluxProUltraInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai FLUX1.1 [pro] ultra model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalFluxProUltraGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "num_images": inputs.num_images,
            "enable_safety_checker": inputs.enable_safety_checker,
            "safety_tolerance": inputs.safety_tolerance,
            "output_format": inputs.output_format,
            "enhance_prompt": inputs.enhance_prompt,
            "raw": inputs.raw,
            "sync_mode": inputs.sync_mode,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/flux-pro/v1.1-ultra",
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
            width = image_data.get("width", 1024)
            height = image_data.get("height", 1024)

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

    async def estimate_cost(self, inputs: FluxProUltraInput) -> float:
        """Estimate cost for FLUX1.1 [pro] ultra generation.

        FLUX1.1 [pro] ultra billing is based on megapixels (rounded up).
        The aspect ratios map to different resolutions, all roughly in the 2-4MP range.
        Estimated at approximately $0.04 per image based on typical resolutions.
        """
        # Approximate cost per image (varies slightly by resolution/megapixels)
        # Most aspect ratios result in 2-4 megapixels
        cost_per_image = 0.04
        return cost_per_image * inputs.num_images
