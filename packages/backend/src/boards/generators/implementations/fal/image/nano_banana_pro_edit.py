"""
fal.ai nano-banana-pro image editing generator.

Edit images using fal.ai's nano-banana-pro/edit model (powered by Google's latest
image generation and editing model). Specializes in realism and typography.

See: https://fal.ai/models/fal-ai/nano-banana-pro/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class NanoBananaProEditInput(BaseModel):
    """Input schema for nano-banana-pro image editing.

    Artifact fields (like image_sources) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        min_length=3,
        max_length=50000,
        description="The prompt for image editing",
    )
    image_sources: list[ImageArtifact] = Field(
        description="List of input images for editing (from previous generations)",
        min_length=1,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate",
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
        description=(
            "Aspect ratio for generated images. Default is 'auto', which takes one "
            "of the input images' aspect ratio"
        ),
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
        default=False,
        description=(
            "If True, the media will be returned as a data URI and the output "
            "data won't be available in the request history"
        ),
    )
    enable_web_search: bool = Field(
        default=False,
        description="Enable web search for generating images with current information",
    )
    limit_generations: bool = Field(
        default=False,
        description=(
            "Experimental parameter to limit the number of generations from each "
            "round of prompting to 1. Set to True to disregard any instructions in "
            "the prompt regarding the number of images to generate"
        ),
    )


class FalNanoBananaProEditGenerator(BaseGenerator):
    """nano-banana-pro image editing generator using fal.ai.

    Google's state-of-the-art image generation and editing model, specializing
    in realism and typography applications.
    """

    name = "fal-nano-banana-pro-edit"
    artifact_type = "image"
    description = (
        "Fal: nano-banana-pro edit - Google's state-of-the-art image editing "
        "with excellent realism and typography"
    )

    def get_input_schema(self) -> type[NanoBananaProEditInput]:
        return NanoBananaProEditInput

    async def generate(
        self, inputs: NanoBananaProEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using fal.ai nano-banana-pro/edit model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalNanoBananaProEditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal(inputs.image_sources, context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_urls": image_urls,
            "num_images": inputs.num_images,
            "aspect_ratio": inputs.aspect_ratio,
            "resolution": inputs.resolution,
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
            "enable_web_search": inputs.enable_web_search,
            "limit_generations": inputs.limit_generations,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/nano-banana-pro/edit",
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

        # Extract image URLs and description from result
        # fal.ai returns: {
        #   "images": [{"url": "...", "width": ..., "height": ...}, ...],
        #   "description": "Text description from the model"
        # }
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            # Extract dimensions if available, otherwise use sensible defaults
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

    async def estimate_cost(self, inputs: NanoBananaProEditInput) -> float:
        """Estimate cost for nano-banana-pro edit generation.

        nano-banana-pro/edit uses Google's latest image editing model.
        Using the same pricing as nano-banana-pro text-to-image.
        """
        # $0.039 per image
        return 0.039 * inputs.num_images
