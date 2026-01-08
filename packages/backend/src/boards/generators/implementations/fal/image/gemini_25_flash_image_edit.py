"""
Google Gemini 2.5 Flash Image edit image-to-image generator.

Google's state-of-the-art image generation and editing model available through fal.ai.
Performs image-to-image transformations and edits based on text prompts.
Supports multiple aspect ratios and output formats with batch generation up to 4 images.

Based on Fal AI's fal-ai/gemini-25-flash-image/edit model.
See: https://fal.ai/models/fal-ai/gemini-25-flash-image/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Gemini25FlashImageEditInput(BaseModel):
    """Input schema for Gemini 2.5 Flash Image edit generation.

    Artifact fields (like image_sources) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="The editing instruction for image transformation",
        min_length=3,
        max_length=5000,
    )
    image_sources: list[ImageArtifact] = Field(
        description="List of input images for editing (from previous generations)",
        min_length=1,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (max 4)",
    )
    aspect_ratio: (
        Literal[
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
        ]
        | None
    ) = Field(
        default="auto",
        description="Image aspect ratio. Default 'auto' uses input image's aspect ratio.",
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


class FalGemini25FlashImageEditGenerator(BaseGenerator):
    """Google Gemini 2.5 Flash Image edit generator using fal.ai."""

    name = "fal-gemini-25-flash-image-edit"
    artifact_type = "image"
    description = "Fal: Gemini 2.5 Flash Image Edit - AI-powered image editing with Gemini"

    def get_input_schema(self) -> type[Gemini25FlashImageEditInput]:
        return Gemini25FlashImageEditInput

    async def generate(
        self, inputs: Gemini25FlashImageEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using Google Gemini 2.5 Flash Image via fal.ai."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalGemini25FlashImageEditGenerator. "
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
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
            "limit_generations": inputs.limit_generations,
        }

        # Add aspect_ratio if provided
        if inputs.aspect_ratio is not None:
            arguments["aspect_ratio"] = inputs.aspect_ratio

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/gemini-25-flash-image/edit",
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
        #   "images": [{"url": "...", "width": ..., "height": ..., ...}, ...],
        #   "description": "Text description from Gemini"
        # }
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

    async def estimate_cost(self, inputs: Gemini25FlashImageEditInput) -> float:
        """Estimate cost for Gemini 2.5 Flash Image edit generation.

        Note: Pricing information not available in fal.ai documentation.
        Using placeholder estimate similar to other Gemini-based models.
        """
        # Placeholder cost estimate per image (similar to nano-banana which also uses Gemini)
        per_image_cost = 0.039
        return per_image_cost * inputs.num_images
