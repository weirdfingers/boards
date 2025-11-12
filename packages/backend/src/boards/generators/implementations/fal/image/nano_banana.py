"""
fal.ai nano-banana text-to-image generator.

Fast image generation using fal.ai's nano-banana model with support for batch outputs.
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class NanoBananaInput(BaseModel):
    """Input schema for nano-banana image generation."""

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
        description="Image aspect ratio and resolution",
    )
    num_inference_steps: int = Field(
        default=4,
        ge=1,
        le=50,
        description="Number of inference steps (more steps = higher quality but slower)",
    )
    guidance_scale: float = Field(
        default=3.5,
        ge=1.0,
        le=20.0,
        description="Guidance scale for prompt adherence",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of images to generate in batch",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter unsafe content",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    sync_mode: bool = Field(
        default=True,
        description="Use synchronous mode (wait for completion)",
    )
    output_format: Literal["jpeg", "png"] = Field(
        default="jpeg",
        description="Output image format",
    )


class FalNanoBananaGenerator(BaseGenerator):
    """nano-banana image generator using fal.ai."""

    name = "fal-nano-banana"
    artifact_type = "image"
    description = "Fal: nano-banana - fast text-to-image generation with batch support"

    def get_input_schema(self) -> type[NanoBananaInput]:
        return NanoBananaInput

    async def generate(
        self, inputs: NanoBananaInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai nano-banana model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for NanoBananaGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_size": inputs.image_size,
            "num_inference_steps": inputs.num_inference_steps,
            "guidance_scale": inputs.guidance_scale,
            "num_images": inputs.num_images,
            "enable_safety_checker": inputs.enable_safety_checker,
            "sync_mode": inputs.sync_mode,
            "output_format": inputs.output_format,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/nano-banana",
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

    async def estimate_cost(self, inputs: NanoBananaInput) -> float:
        """Estimate cost for nano-banana generation.

        nano-banana typically costs around $0.003 per image.
        """
        return 0.003 * inputs.num_images  # $0.003 per image, scaled by batch size
