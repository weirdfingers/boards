"""
fal.ai FLUX.2 [dev] text-to-image generator.

High-quality image generation using fal.ai's FLUX.2 [dev] model from Black Forest Labs.
Features enhanced realism, crisper text generation, and configurable acceleration.

See: https://fal.ai/models/fal-ai/flux-2
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Flux2Input(BaseModel):
    """Input schema for FLUX.2 [dev] image generation."""

    prompt: str = Field(description="The text prompt for image generation")
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate in batch (max 4)",
    )
    image_size: Literal[
        "square_hd",
        "square",
        "portrait_4_3",
        "portrait_16_9",
        "landscape_4_3",
        "landscape_16_9",
    ] = Field(
        default="landscape_4_3",
        description="Predefined image size/aspect ratio",
    )
    acceleration: Literal["none", "regular", "high"] = Field(
        default="regular",
        description="Processing speed level (none = highest quality, high = fastest)",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    enable_prompt_expansion: bool = Field(
        default=False,
        description="Enhance prompt automatically for better results",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter NSFW content",
    )
    guidance_scale: float = Field(
        default=2.5,
        ge=0.0,
        le=20.0,
        description="Adherence strength to input prompt (0-20)",
    )
    num_inference_steps: int = Field(
        default=28,
        ge=4,
        le=50,
        description="Number of inference steps (4-50, higher = better quality but slower)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    sync_mode: bool = Field(
        default=True,
        description="Use synchronous mode (wait for completion)",
    )


class FalFlux2Generator(BaseGenerator):
    """FLUX.2 [dev] image generator using fal.ai."""

    name = "fal-flux-2"
    artifact_type = "image"
    description = (
        "Fal: FLUX.2 [dev] - enhanced realism, crisper text generation, "
        "and native editing capabilities from Black Forest Labs"
    )

    def get_input_schema(self) -> type[Flux2Input]:
        return Flux2Input

    async def generate(
        self, inputs: Flux2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai FLUX.2 [dev] model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalFlux2Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "image_size": inputs.image_size,
            "acceleration": inputs.acceleration,
            "output_format": inputs.output_format,
            "enable_prompt_expansion": inputs.enable_prompt_expansion,
            "enable_safety_checker": inputs.enable_safety_checker,
            "guidance_scale": inputs.guidance_scale,
            "num_inference_steps": inputs.num_inference_steps,
            "sync_mode": inputs.sync_mode,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/flux-2",
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

    async def estimate_cost(self, inputs: Flux2Input) -> float:
        """Estimate cost for FLUX.2 [dev] generation.

        FLUX.2 [dev] pricing is approximately $0.055 per image based on
        typical FLUX model pricing. Cost varies slightly based on
        acceleration level and inference steps.
        """
        # Approximate cost per image
        cost_per_image = 0.055
        return cost_per_image * inputs.num_images
