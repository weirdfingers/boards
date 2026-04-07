"""
fal.ai ByteDance Seedream v5.0 Lite Edit image editing generator.

Edit images using fal.ai's ByteDance Seedream v5.0 Lite Edit model.
Seedream 5.0 is ByteDance's latest generation image model with improved
editing capabilities. The Lite variant supports editing up to 10 input
images with a text prompt, with max resolution of 3072x3072 (9MP).

See: https://fal.ai/models/fal-ai/bytedance/seedream/v5/lite/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult

# Valid image size presets
ImageSizePreset = Literal[
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
    "auto_2K",
    "auto_4K",
]


class BytedanceSeedreamV5LiteEditInput(BaseModel):
    """Input schema for ByteDance Seedream v5.0 Lite Edit.

    Artifact fields (like image_sources) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(description="The text prompt used to edit the image")
    image_sources: list[ImageArtifact] = Field(
        description="List of input images for editing (up to 10 images)",
        min_length=1,
        max_length=10,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=6,
        description="Number of images to generate",
    )
    image_size: ImageSizePreset | None = Field(
        default=None,
        description=(
            "The size of the generated image. Options: square_hd, square, "
            "portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9, "
            "auto_2K, auto_4K. Default is 2048x2048"
        ),
    )
    seed: int | None = Field(
        default=None,
        description="Random seed to control the stochasticity of image generation",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enables safety filtering on generated images",
    )


class FalBytedanceSeedreamV5LiteEditGenerator(BaseGenerator):
    """ByteDance Seedream v5.0 Lite Edit image editing generator using fal.ai."""

    name = "fal-bytedance-seedream-v5-lite-edit"
    artifact_type = "image"
    description = "Fal: ByteDance Seedream 5.0 Lite Edit - Latest generation image editing"

    def get_input_schema(self) -> type[BytedanceSeedreamV5LiteEditInput]:
        return BytedanceSeedreamV5LiteEditInput

    async def generate(
        self, inputs: BytedanceSeedreamV5LiteEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using fal.ai ByteDance Seedream v5.0 Lite Edit model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBytedanceSeedreamV5LiteEditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal(inputs.image_sources, context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "image_urls": image_urls,
            "num_images": inputs.num_images,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Add optional parameters
        if inputs.image_size is not None:
            arguments["image_size"] = inputs.image_size

        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/bytedance/seedream/v5/lite/edit",
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
                                progress=50.0,
                                phase="processing",
                                message=message,
                            )
                        )

        # Get final result
        result = await handler.get()

        # Extract image URLs from result
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            width = image_data.get("width", 2048)
            height = image_data.get("height", 2048)

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Determine format from content_type or default to png
            content_type = image_data.get("content_type", "image/png")
            if "jpeg" in content_type or "jpg" in content_type:
                format_type = "jpeg"
            elif "webp" in content_type:
                format_type = "webp"
            else:
                format_type = "png"

            # Store with appropriate output_index
            artifact = await context.store_image_result(
                storage_url=image_url,
                format=format_type,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: BytedanceSeedreamV5LiteEditInput) -> float:
        """Estimate cost for ByteDance Seedream v5.0 Lite Edit generation.

        Seedream 5.0 Lite pricing is approximately $0.035 per image.
        """
        return 0.035 * inputs.num_images
