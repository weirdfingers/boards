"""
fal.ai Ideogram V3 Character Edit generator.

Modify consistent characters while preserving their core identity.
Edit poses, expressions, or clothing without losing recognizable character features.

Based on Fal AI's fal-ai/ideogram/character/edit model.
See: https://fal.ai/models/fal-ai/ideogram/character/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class RGBColor(BaseModel):
    """RGB color definition."""

    r: int = Field(default=0, ge=0, le=255, description="Red color value")
    g: int = Field(default=0, ge=0, le=255, description="Green color value")
    b: int = Field(default=0, ge=0, le=255, description="Blue color value")


class ColorPaletteMember(BaseModel):
    """Color palette member with RGB color and weight."""

    rgb: RGBColor = Field(description="RGB color definition")
    color_weight: float = Field(
        default=0.5,
        ge=0.05,
        le=1.0,
        description="The weight of the color in the color palette",
    )


class ColorPalette(BaseModel):
    """Color palette for generation.

    Can be specified via presets or explicit hexadecimal representations.
    """

    name: (
        Literal[
            "EMBER",
            "FRESH",
            "JUNGLE",
            "MAGIC",
            "MELON",
            "MOSAIC",
            "PASTEL",
            "ULTRAMARINE",
        ]
        | None
    ) = Field(default=None, description="Preset color palette name")
    members: list[ColorPaletteMember] | None = Field(
        default=None,
        description="Explicit color palette members with RGB values and weights",
    )


class IdeogramCharacterEditInput(BaseModel):
    """Input schema for Ideogram Character Edit.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    prompt: str = Field(description="The prompt to fill the masked part of the image")
    image_url: ImageArtifact = Field(
        description=(
            "The image to generate from. MUST have the exact same dimensions as the mask image"
        )
    )
    mask_url: ImageArtifact = Field(
        description=(
            "The mask to inpaint the image. MUST have the exact same dimensions as the input image"
        )
    )
    reference_image_urls: list[ImageArtifact] = Field(
        description=(
            "A set of images to use as character references. "
            "Currently only 1 image is supported, rest will be ignored "
            "(maximum total size 10MB)"
        ),
        min_length=1,
    )
    style: Literal["AUTO", "REALISTIC", "FICTION"] = Field(
        default="AUTO",
        description="The style type to generate with. Cannot be used with style_codes",
    )
    expand_prompt: bool = Field(
        default=True,
        description="Determine if MagicPrompt should be used in generating the request or not",
    )
    rendering_speed: Literal["TURBO", "BALANCED", "QUALITY"] = Field(
        default="BALANCED",
        description="The rendering speed to use",
    )
    reference_mask_urls: list[ImageArtifact] | None = Field(
        default=None,
        description=(
            "A set of masks to apply to character references. "
            "Currently only 1 mask is supported (maximum total size 10MB)"
        ),
    )
    image_urls: list[ImageArtifact] | None = Field(
        default=None,
        description="A set of images to use as style references (maximum total size 10MB)",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Number of images to generate",
    )
    style_codes: list[str] | None = Field(
        default=None,
        description="A list of 8 character hexadecimal codes representing the style of the image",
    )
    color_palette: ColorPalette | None = Field(
        default=None,
        description="A color palette for generation",
    )
    sync_mode: bool = Field(
        default=False,
        description=(
            "If True, the media will be returned as a data URI "
            "and output data won't be available in request history"
        ),
    )
    seed: int | None = Field(
        default=None,
        description="Seed for the random number generator",
    )


class FalIdeogramCharacterEditGenerator(BaseGenerator):
    """Generator for Ideogram V3 Character Edit - modify consistent characters."""

    name = "fal-ideogram-character-edit"
    artifact_type = "image"
    description = (
        "Fal: Ideogram V3 Character Edit - "
        "Modify consistent characters while preserving their core identity"
    )

    def get_input_schema(self) -> type[IdeogramCharacterEditInput]:
        """Return the input schema for this generator."""
        return IdeogramCharacterEditInput

    async def generate(
        self, inputs: IdeogramCharacterEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate edited character images using fal.ai ideogram/character/edit."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalIdeogramCharacterEditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        # Upload required artifacts
        image_url = await upload_artifacts_to_fal([inputs.image_url], context)
        mask_url = await upload_artifacts_to_fal([inputs.mask_url], context)
        reference_image_urls = await upload_artifacts_to_fal(inputs.reference_image_urls, context)

        # Upload optional artifacts
        reference_mask_urls = None
        if inputs.reference_mask_urls:
            reference_mask_urls = await upload_artifacts_to_fal(inputs.reference_mask_urls, context)

        style_reference_urls = None
        if inputs.image_urls:
            style_reference_urls = await upload_artifacts_to_fal(inputs.image_urls, context)

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": image_url[0],  # Single URL
            "mask_url": mask_url[0],  # Single URL
            "reference_image_urls": reference_image_urls,  # Array
            "style": inputs.style,
            "expand_prompt": inputs.expand_prompt,
            "rendering_speed": inputs.rendering_speed,
            "num_images": inputs.num_images,
            "sync_mode": inputs.sync_mode,
        }

        # Add optional parameters
        if reference_mask_urls:
            arguments["reference_mask_urls"] = reference_mask_urls

        if style_reference_urls:
            arguments["image_urls"] = style_reference_urls

        if inputs.style_codes:
            arguments["style_codes"] = inputs.style_codes

        if inputs.color_palette:
            # Convert Pydantic model to dict for API
            arguments["color_palette"] = inputs.color_palette.model_dump(exclude_none=True)

        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/ideogram/character/edit",
            arguments=arguments,
        )

        # Store external job ID
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates
        from .....progress.models import ProgressUpdate

        event_count = 0
        async for event in handler.iter_events(with_logs=True):
            event_count += 1
            # Sample every 3rd event to avoid spam
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

        # Extract images from result
        # API returns: {"images": [{"url": "...", ...}], "seed": 123}
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Extract dimensions if available (Ideogram typically generates at fixed sizes)
            width = image_data.get("width", 1024)
            height = image_data.get("height", 1024)

            # Determine format from content_type or default to webp
            content_type = image_data.get("content_type", "image/webp")
            format_str = content_type.split("/")[-1] if "/" in content_type else "webp"

            artifact = await context.store_image_result(
                storage_url=image_url,
                format=format_str,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: IdeogramCharacterEditInput) -> float:
        """Estimate cost for this generation in USD.

        Pricing information not available in documentation.
        Using estimated cost of $0.05 per image.
        """
        cost_per_image = 0.05
        return cost_per_image * inputs.num_images
