"""
fal.ai nano-banana-2 text-to-image generator.

Google's state-of-the-art fast image generation model with support for
multiple resolutions, aspect ratios, and optional web search integration.

Based on Fal AI's fal-ai/nano-banana-2 model.
See: https://fal.ai/models/fal-ai/nano-banana-2
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class NanoBanana2Input(BaseModel):
    """Input schema for nano-banana-2 image generation."""

    prompt: str = Field(
        min_length=3,
        max_length=50000,
        description="The text prompt to generate an image from",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate in batch",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    aspect_ratio: Literal[
        "auto",
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
        default="auto",
        description="Image aspect ratio",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    safety_tolerance: Literal["1", "2", "3", "4", "5", "6"] = Field(
        default="4",
        description="Safety tolerance level (1 = strictest, 6 = most permissive)",
    )
    resolution: Literal["0.5K", "1K", "2K", "4K"] = Field(
        default="1K",
        description="Image resolution",
    )
    limit_generations: bool = Field(
        default=True,
        description="Experimental: restrict to 1 generation per round",
    )
    enable_web_search: bool = Field(
        default=False,
        description="Allow web data to inform generation",
    )
    sync_mode: bool = Field(
        default=True,
        description="Use synchronous mode (wait for completion)",
    )


class FalNanoBanana2Generator(BaseGenerator):
    """nano-banana-2 image generator using fal.ai.

    Google's state-of-the-art fast image generation model with support for
    multiple resolutions, aspect ratios, and optional web search.
    """

    name = "fal-nano-banana-2"
    artifact_type = "image"
    description = (
        "Fal: nano-banana-2 - Google's fast image generation "
        "with web search and multiple resolutions"
    )

    def get_input_schema(self) -> type[NanoBanana2Input]:
        return NanoBanana2Input

    async def generate(
        self, inputs: NanoBanana2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai nano-banana-2 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalNanoBanana2Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments: dict[str, object] = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "aspect_ratio": inputs.aspect_ratio,
            "output_format": inputs.output_format,
            "safety_tolerance": inputs.safety_tolerance,
            "resolution": inputs.resolution,
            "limit_generations": inputs.limit_generations,
            "enable_web_search": inputs.enable_web_search,
            "sync_mode": inputs.sync_mode,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/nano-banana-2",
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

    async def estimate_cost(self, inputs: NanoBanana2Input) -> float:
        """Estimate cost for nano-banana-2 generation.

        Base cost is $0.08 per image at 1K resolution.
        Resolution multipliers: 0.5K=0.75x, 2K=1.5x, 4K=2x.
        Web search adds $0.015 per request.
        """
        resolution_multipliers = {
            "0.5K": 0.75,
            "1K": 1.0,
            "2K": 1.5,
            "4K": 2.0,
        }
        multiplier = resolution_multipliers.get(inputs.resolution, 1.0)
        cost = 0.08 * multiplier * inputs.num_images

        if inputs.enable_web_search:
            cost += 0.015

        return cost
