"""
fal.ai nano-banana-pro text-to-image generator.

State-of-the-art image generation using Google's latest model, specializing in
realism and typography applications.

See: https://fal.ai/models/fal-ai/nano-banana-pro
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class NanoBananaProInput(BaseModel):
    """Input schema for nano-banana-pro image generation."""

    prompt: str = Field(
        min_length=3,
        max_length=50000,
        description="The text prompt to generate an image from",
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
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate in batch",
    )
    resolution: Literal["1K", "2K", "4K"] = Field(
        default="1K",
        description="Image resolution (1K, 2K, or 4K)",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    sync_mode: bool = Field(
        default=True,
        description="Use synchronous mode (wait for completion)",
    )


class FalNanoBananaProGenerator(BaseGenerator):
    """nano-banana-pro image generator using fal.ai.

    Google's state-of-the-art image generation and editing model, specializing
    in realism and typography applications.
    """

    name = "fal-nano-banana-pro"
    artifact_type = "image"
    description = (
        "Fal: nano-banana-pro - Google's state-of-the-art image generation "
        "with excellent realism and typography"
    )

    def get_input_schema(self) -> type[NanoBananaProInput]:
        return NanoBananaProInput

    async def generate(
        self, inputs: NanoBananaProInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai nano-banana-pro model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for NanoBananaProGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "num_images": inputs.num_images,
            "resolution": inputs.resolution,
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/nano-banana-pro",
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

    async def estimate_cost(self, inputs: NanoBananaProInput) -> float:
        """Estimate cost for nano-banana-pro generation.

        nano-banana-pro is a premium model costing approximately $0.039 per image.
        """
        return 0.039 * inputs.num_images  # $0.039 per image, scaled by batch size
