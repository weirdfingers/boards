"""
fal.ai FLUX 2 Pro Edit generator.

Production-grade multi-reference image editing that combines up to 9 reference
images through a streamlined pipeline for professional image manipulation.
Supports natural language precision, explicit image indexing with @ symbol,
and zero-configuration workflow.

Based on Fal AI's fal-ai/flux-2-pro/edit model.
See: https://fal.ai/models/fal-ai/flux-2-pro/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult

# Image size presets supported by the API
ImageSizePreset = Literal[
    "auto",
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
]


class Flux2ProEditInput(BaseModel):
    """Input schema for FLUX 2 Pro Edit.

    Artifact fields (like image_sources) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="The prompt to edit the images. Use @ symbol to reference "
        "specific input images by index (e.g., '@1' for first image)."
    )
    image_sources: list[ImageArtifact] = Field(
        description="List of input images for editing (up to 9 images, 9 MP total)",
        min_length=1,
        max_length=9,
    )
    image_size: ImageSizePreset | None = Field(
        default="auto",
        description="The size of the generated image. If 'auto', the size will be "
        "determined by the model based on input images.",
    )
    output_format: Literal["jpeg", "png"] = Field(
        default="jpeg",
        description="The format of the generated image.",
    )
    sync_mode: bool = Field(
        default=False,
        description=(
            "If True, the media will be returned as a data URI and the output "
            "data won't be available in the request history."
        ),
    )
    safety_tolerance: Literal["1", "2", "3", "4", "5"] = Field(
        default="2",
        description=(
            "The safety tolerance level for the generated image. "
            "1 is most strict, 5 is most permissive."
        ),
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Whether to enable the safety checker.",
    )
    seed: int | None = Field(
        default=None,
        description="The seed to use for the generation. Leave empty for random.",
    )


class FalFlux2ProEditGenerator(BaseGenerator):
    """FLUX 2 Pro Edit image generator using fal.ai.

    Production-grade multi-reference editing that combines up to 9 reference
    images through a streamlined pipeline. Supports natural language precision
    for describing complex edits without masks.
    """

    name = "fal-flux-2-pro-edit"
    artifact_type = "image"
    description = "Fal: FLUX 2 Pro Edit - Production-grade multi-reference image editing"

    def get_input_schema(self) -> type[Flux2ProEditInput]:
        return Flux2ProEditInput

    async def generate(
        self, inputs: Flux2ProEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using fal.ai FLUX 2 Pro Edit model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalFlux2ProEditGenerator. "
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
        arguments: dict = {
            "prompt": inputs.prompt,
            "image_urls": image_urls,
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
            "safety_tolerance": inputs.safety_tolerance,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Add optional parameters
        if inputs.image_size is not None:
            arguments["image_size"] = inputs.image_size
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/flux-2-pro/edit",
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
        # fal.ai returns: {
        #   "images": [{"url": "...", "width": ..., "height": ..., ...}, ...],
        #   "seed": ...
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

    async def estimate_cost(self, inputs: Flux2ProEditInput) -> float:
        """Estimate cost for FLUX 2 Pro Edit generation.

        Pricing: $0.03 for first megapixel, $0.015 for additional megapixels.
        Using base cost of $0.03 as default (1 MP output).
        """
        # Base cost per generation (1 megapixel default)
        base_cost = 0.03
        return base_cost
