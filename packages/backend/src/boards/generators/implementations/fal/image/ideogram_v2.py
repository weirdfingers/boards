"""
Generate high-quality images, posters, and logos with exceptional typography handling.

Based on Fal AI's fal-ai/ideogram/v2 model.
See: https://fal.ai/models/fal-ai/ideogram/v2
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class IdeogramV2Input(BaseModel):
    """Input schema for Ideogram V2 image generation.

    Ideogram V2 is optimized for generating high-quality images with exceptional
    typography handling, making it ideal for posters, logos, and creative content.
    """

    prompt: str = Field(description="Text description for image generation")
    aspect_ratio: Literal[
        "1:1",
        "16:9",
        "9:16",
        "4:3",
        "3:4",
        "10:16",
        "16:10",
        "1:3",
        "3:1",
        "3:2",
        "2:3",
    ] = Field(
        default="1:1",
        description="Aspect ratio for the generated image",
    )
    style: Literal["auto", "general", "realistic", "design", "render_3D", "anime"] = Field(
        default="auto",
        description="Visual style for the generated image",
    )
    expand_prompt: bool = Field(
        default=True,
        description="Enable MagicPrompt functionality to enhance the prompt",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    negative_prompt: str = Field(
        default="",
        description="Elements to exclude from the generated image",
    )
    sync_mode: bool = Field(
        default=False,
        description="Use synchronous mode (returns data URI instead of storing in history)",
    )


class FalIdeogramV2Generator(BaseGenerator):
    """Generator for high-quality images with exceptional typography using Ideogram V2."""

    name = "fal-ideogram-v2"
    artifact_type = "image"
    description = (
        "Fal: Ideogram V2 - high-quality images, posters, and logos with exceptional typography"
    )

    def get_input_schema(self) -> type[IdeogramV2Input]:
        """Return the input schema for this generator."""
        return IdeogramV2Input

    async def generate(
        self, inputs: IdeogramV2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai Ideogram V2 model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalIdeogramV2Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "aspect_ratio": inputs.aspect_ratio,
            "style": inputs.style,
            "expand_prompt": inputs.expand_prompt,
            "negative_prompt": inputs.negative_prompt,
            "sync_mode": inputs.sync_mode,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/ideogram/v2",
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
        # fal.ai ideogram/v2 returns:
        # {"images": [{"url": "...", "content_type": "...", ...}], "seed": ...}
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
            # Ideogram V2 doesn't return explicit width/height in the response schema,
            # so we'll use reasonable defaults based on aspect ratio
            width = image_data.get("width", 1024)
            height = image_data.get("height", 1024)

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

    async def estimate_cost(self, inputs: IdeogramV2Input) -> float:
        """Estimate cost for Ideogram V2 generation.

        Ideogram V2 pricing is approximately $0.04 per image generation.
        Note: Actual pricing may vary. Check Fal AI documentation for current rates.
        """
        return 0.04  # $0.04 per image (estimate)
