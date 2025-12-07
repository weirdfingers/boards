"""
fal.ai FLUX.2 [pro] text-to-image generator.

Production-optimized generation with professional quality out of the box.
Studio-grade images through a streamlined pipeline that prioritizes consistency
and speed over parameter tuning.

Based on Fal AI's fal-ai/flux-2-pro model.
See: https://fal.ai/models/fal-ai/flux-2-pro
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Flux2ProInput(BaseModel):
    """Input schema for FLUX.2 [pro] image generation.

    Note: FLUX.2 [pro] is designed for zero-configuration quality with
    no inference steps or guidance parameters to adjust.
    """

    prompt: str = Field(description="Text prompt for image generation")
    image_size: Literal[
        "square_hd",
        "square",
        "portrait_4_3",
        "portrait_16_9",
        "landscape_4_3",
        "landscape_16_9",
    ] = Field(
        default="landscape_4_3",
        description="Image size preset. Available presets: square_hd, square, "
        "portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9",
    )
    output_format: Literal["jpeg", "png"] = Field(
        default="jpeg",
        description="Output image format. JPEG for optimized file sizes, PNG for lossless quality",
    )
    safety_tolerance: Literal["1", "2", "3", "4", "5"] = Field(
        default="2",
        description="Safety tolerance level (1 = most strict, 5 = most permissive)",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter unsafe content",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible generation (optional)",
    )
    sync_mode: bool = Field(
        default=True,
        description="Use synchronous mode (wait for completion)",
    )


# Approximate megapixels for each preset
_SIZE_MEGAPIXELS = {
    "square_hd": 1.5,  # ~1408x1408 (typical HD square)
    "square": 1.0,  # ~1024x1024
    "portrait_4_3": 1.0,  # ~768x1024
    "portrait_16_9": 1.0,  # ~576x1024
    "landscape_4_3": 1.0,  # ~1024x768
    "landscape_16_9": 1.0,  # ~1024x576
}


class FalFlux2ProGenerator(BaseGenerator):
    """FLUX.2 [pro] image generator using fal.ai.

    Production-optimized generation with professional quality out of the box.
    Zero-configuration quality with no inference steps or guidance parameters
    to adjust. Predictable results across batch generations.
    """

    name = "fal-flux-2-pro"
    artifact_type = "image"
    description = "Fal: FLUX.2 [pro] - production-optimized text-to-image with studio-grade quality"

    def get_input_schema(self) -> type[Flux2ProInput]:
        return Flux2ProInput

    async def generate(
        self, inputs: Flux2ProInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate image using fal.ai FLUX.2 [pro] model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalFlux2ProGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_size": inputs.image_size,
            "output_format": inputs.output_format,
            "safety_tolerance": inputs.safety_tolerance,
            "enable_safety_checker": inputs.enable_safety_checker,
            "sync_mode": inputs.sync_mode,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/flux-2-pro",
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

    async def estimate_cost(self, inputs: Flux2ProInput) -> float:
        """Estimate cost for FLUX.2 [pro] generation.

        FLUX.2 [pro] billing is based on megapixels (rounded up):
        - $0.03 for the first megapixel
        - $0.015 per additional megapixel

        For preset sizes, we estimate based on typical dimensions.
        """
        megapixels = _SIZE_MEGAPIXELS.get(inputs.image_size, 1.0)

        # First megapixel is $0.03, each additional is $0.015
        if megapixels <= 1:
            return 0.03
        else:
            additional_megapixels = megapixels - 1
            return 0.03 + (additional_megapixels * 0.015)
