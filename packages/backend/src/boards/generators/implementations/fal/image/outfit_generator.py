"""
Outfit Generator - Composite generator for virtual try-on with multiple garments.

Orchestrates sequential Kolors Virtual Try-On calls to apply multiple garments
onto a model photo. Each garment is applied in layering order, with each
intermediate result becoming the input for the next step.

Based on the pipeline design from ticket at-31t4.
"""

import os
from typing import Self

from pydantic import BaseModel, Field, model_validator

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult

# Layering order: inner/covered layers first, outer/visible layers last
GARMENT_SLOTS = [
    ("socks_image", "Socks"),
    ("inside_top_image", "Inside Top"),
    ("bottoms_image", "Bottoms"),
    ("outside_top_image", "Outside Top"),
    ("shoes_image", "Shoes"),
    ("hat_image", "Hat"),
]


class OutfitGeneratorInput(BaseModel):
    """Input schema for OutfitGenerator.

    Requires a model image and at least one garment image.
    Garments are applied in layering order (inner first, outer last).
    """

    model_image: ImageArtifact = Field(
        description="Image of the person to dress",
    )
    inside_top_image: ImageArtifact | None = Field(
        default=None,
        description="Image of the inside top / base layer garment",
    )
    outside_top_image: ImageArtifact | None = Field(
        default=None,
        description="Image of the outside top / jacket / coat garment",
    )
    bottoms_image: ImageArtifact | None = Field(
        default=None,
        description="Image of the bottoms / pants / skirt garment",
    )
    shoes_image: ImageArtifact | None = Field(
        default=None,
        description="Image of the shoes",
    )
    socks_image: ImageArtifact | None = Field(
        default=None,
        description="Image of the socks",
    )
    hat_image: ImageArtifact | None = Field(
        default=None,
        description="Image of the hat",
    )

    @model_validator(mode="after")
    def at_least_one_garment(self) -> Self:
        """Validate that at least one garment slot is provided."""
        has_garment = any(getattr(self, field_name) is not None for field_name, _ in GARMENT_SLOTS)
        if not has_garment:
            raise ValueError("At least one garment image must be provided")
        return self


class OutfitGenerator(BaseGenerator):
    """Composite generator that applies multiple garments via sequential Kolors calls."""

    name = "outfit-generator"
    artifact_type = "image"
    description = "Apply multiple garments onto a model photo using sequential virtual try-on"

    def get_input_schema(self) -> type[OutfitGeneratorInput]:
        """Return the input schema for this generator."""
        return OutfitGeneratorInput

    async def generate(
        self, inputs: OutfitGeneratorInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate outfit by sequentially applying garments via Kolors Virtual Try-On."""
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for OutfitGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        from .....progress.models import ProgressUpdate
        from ..utils import upload_artifacts_to_fal

        # Build ordered list of (slot_name, artifact) for non-None garments
        garments: list[tuple[str, ImageArtifact]] = []
        for field_name, slot_name in GARMENT_SLOTS:
            artifact = getattr(inputs, field_name)
            if artifact is not None:
                garments.append((slot_name, artifact))

        total = len(garments)

        # Upload model image to Fal
        model_urls = await upload_artifacts_to_fal([inputs.model_image], context)
        current_image_url = model_urls[0]

        await context.publish_progress(
            ProgressUpdate(
                job_id="outfit-generator",
                status="initializing",
                progress=0.0,
                phase="initializing",
                message="Initializing...",
            )
        )

        # Apply each garment sequentially
        last_result: dict = {}
        for i, (slot_name, garment_artifact) in enumerate(garments, start=1):
            await context.publish_progress(
                ProgressUpdate(
                    job_id="outfit-generator",
                    status="processing",
                    progress=(i - 1) / total * 100,
                    phase="processing",
                    message=f"Applying {slot_name} ({i}/{total})...",
                )
            )

            # Upload garment to Fal
            garment_urls = await upload_artifacts_to_fal([garment_artifact], context)

            # Call Kolors Virtual Try-On
            handler = await fal_client.submit_async(
                "fal-ai/kling/v1-5/kolors-virtual-try-on",
                arguments={
                    "human_image_url": current_image_url,
                    "garment_image_url": garment_urls[0],
                },
            )

            await context.set_external_job_id(handler.request_id)

            # Stream progress events
            async for _event in handler.iter_events(with_logs=True):
                pass  # Consume events to allow processing

            # Get result
            last_result = await handler.get()

            image_data = last_result.get("image")
            if not image_data:
                raise ValueError(f"No image returned from Kolors API for step {i} ({slot_name})")

            image_url = image_data.get("url")
            if not image_url:
                raise ValueError(f"Image missing URL in Kolors response for step {i} ({slot_name})")

            # Use the result URL directly as input for the next step
            # (Fal result URLs are publicly accessible)
            current_image_url = image_url

        await context.publish_progress(
            ProgressUpdate(
                job_id="outfit-generator",
                status="finalizing",
                progress=95.0,
                phase="finalizing",
                message="Finalizing...",
            )
        )

        # Store final result
        final_image_data = last_result.get("image")
        if not final_image_data:
            raise ValueError("No final image produced")

        width = final_image_data.get("width", 768)
        height = final_image_data.get("height", 1024)

        content_type = final_image_data.get("content_type", "image/png")
        if "jpeg" in content_type or "jpg" in content_type:
            format_str = "jpeg"
        else:
            format_str = "png"

        artifact = await context.store_image_result(
            storage_url=current_image_url,
            format=format_str,
            width=width,
            height=height,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: OutfitGeneratorInput) -> float:
        """Estimate cost: $0.05 per garment (one Kolors call each)."""
        count = sum(1 for field_name, _ in GARMENT_SLOTS if getattr(inputs, field_name) is not None)
        return 0.05 * count
