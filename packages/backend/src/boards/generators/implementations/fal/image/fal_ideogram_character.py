"""
Ideogram V3 Character generator - Generate consistent character appearances.

This generator creates images with consistent character appearances across multiple
generations, maintaining facial features, proportions, and distinctive traits for
cohesive storytelling and branding purposes.

Based on Fal AI's fal-ai/ideogram/character model.
See: https://fal.ai/models/fal-ai/ideogram/character
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from .....generators.artifacts import ImageArtifact
from .....generators.base import (
    BaseGenerator,
    GeneratorExecutionContext,
    GeneratorResult,
)
from .....progress.models import ProgressUpdate


class IdeogramCharacterInput(BaseModel):
    """Input schema for fal-ideogram-character.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="The prompt to fill the masked part of the image. Describe the scene, "
        "setting, and action for the character."
    )
    reference_image_urls: list[ImageArtifact] = Field(
        description="A set of images to use as character references. Currently only 1 image "
        "is supported, rest will be ignored. Maximum total size 10MB across all character "
        "references. The images should be in JPEG, PNG or WebP format.",
        min_length=1,
    )
    image_size: str | dict[str, int] = Field(
        default="square_hd",
        description="Size preset (square_hd, square, portrait_4_3, portrait_16_9, "
        "landscape_4_3, landscape_16_9) or custom dimensions with width and height.",
    )
    style: Literal["AUTO", "REALISTIC", "FICTION"] = Field(
        default="AUTO",
        description="The style preset to use for generation.",
    )
    expand_prompt: bool = Field(
        default=True,
        description="Determine if MagicPrompt should be used in generating the request or not.",
    )
    rendering_speed: Literal["TURBO", "BALANCED", "QUALITY"] = Field(
        default="BALANCED",
        description="The speed/quality tradeoff for generation. TURBO is fastest but lower "
        "quality, QUALITY is slowest but highest quality.",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Number of images to generate (1-8).",
    )
    negative_prompt: str | None = Field(
        default=None,
        description="Things to exclude from the generation.",
    )
    sync_mode: bool = Field(
        default=False,
        description="If true, returns data URI instead of URL.",
    )
    seed: int | None = Field(
        default=None,
        description="Random number generator seed for reproducible results.",
    )
    reference_mask_urls: list[ImageArtifact] | None = Field(
        default=None,
        description="Masking images to refine character editing. Maximum 10MB total size. "
        "Currently only 1 mask is supported.",
    )
    image_urls: list[ImageArtifact] | None = Field(
        default=None,
        description="Style reference images. Maximum 10MB total size.",
    )
    style_codes: list[str] | None = Field(
        default=None,
        description="8-character hexadecimal style codes for custom styles.",
    )
    color_palette: dict[str, str | list[dict[str, int]]] | None = Field(
        default=None,
        description="Color palette preset (EMBER, FRESH, JUNGLE, MAGIC, MELON, MOSAIC, "
        "PASTEL, ULTRAMARINE) or custom RGB members.",
    )


class FalIdeogramCharacterGenerator(BaseGenerator):
    """Generator for consistent character appearance generation."""

    name = "fal-ideogram-character"
    description = (
        "Generate consistent character appearances across multiple images. Maintains facial "
        "features, proportions, and distinctive traits for cohesive storytelling and branding."
    )
    artifact_type = "image"

    def get_input_schema(self) -> type[IdeogramCharacterInput]:
        """Return the input schema for this generator."""
        return IdeogramCharacterInput

    async def generate(
        self, inputs: IdeogramCharacterInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images with consistent character appearance using fal.ai ideogram/character."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalIdeogramCharacterGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload artifact inputs to Fal's storage
        from ..utils import upload_artifacts_to_fal

        reference_image_urls = await upload_artifacts_to_fal(inputs.reference_image_urls, context)

        # Prepare arguments for fal.ai API
        arguments: dict = {
            "prompt": inputs.prompt,
            "reference_image_urls": reference_image_urls,
            "image_size": inputs.image_size,
            "style": inputs.style,
            "expand_prompt": inputs.expand_prompt,
            "rendering_speed": inputs.rendering_speed,
            "num_images": inputs.num_images,
            "sync_mode": inputs.sync_mode,
        }

        # Add optional parameters if provided
        if inputs.negative_prompt is not None:
            arguments["negative_prompt"] = inputs.negative_prompt
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed
        if inputs.reference_mask_urls is not None:
            arguments["reference_mask_urls"] = await upload_artifacts_to_fal(
                inputs.reference_mask_urls, context
            )
        if inputs.image_urls is not None:
            arguments["image_urls"] = await upload_artifacts_to_fal(inputs.image_urls, context)
        if inputs.style_codes is not None:
            arguments["style_codes"] = inputs.style_codes
        if inputs.color_palette is not None:
            arguments["color_palette"] = inputs.color_palette

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/ideogram/character",
            arguments=arguments,
        )

        # Store external job ID
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates
        event_count = 0
        async for _event in handler.iter_events(with_logs=True):
            event_count += 1
            # Sample every 3rd event to avoid spam
            if event_count % 3 == 0:
                await context.publish_progress(
                    ProgressUpdate(
                        job_id="",  # Will be populated by context
                        status="processing",
                        progress=0.5,
                        phase="processing",
                    )
                )

        # Get final result
        result = await handler.get()

        # Extract outputs from result and store artifacts
        artifacts = []
        images = result.get("images", [])

        for idx, image_data in enumerate(images):
            # Determine image format from content_type or URL
            content_type = image_data.get("content_type", "image/png")
            image_format = content_type.split("/")[-1] if "/" in content_type else "png"

            # Store image artifact
            artifact = await context.store_image_result(
                storage_url=image_data["url"],
                format=image_format,
                # Image dimensions are not provided in response, use defaults based on size
                width=1024,  # Will be updated when image is downloaded
                height=1024,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: IdeogramCharacterInput) -> float:
        """Estimate cost for this generation in USD.

        Pricing based on rendering speed:
        - TURBO: $0.10 per image
        - BALANCED: $0.15 per image
        - QUALITY: $0.20 per image
        """
        cost_per_image = {
            "TURBO": 0.10,
            "BALANCED": 0.15,
            "QUALITY": 0.20,
        }

        base_cost = cost_per_image.get(inputs.rendering_speed, 0.15)
        return base_cost * inputs.num_images
