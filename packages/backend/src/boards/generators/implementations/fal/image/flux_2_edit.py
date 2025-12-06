"""
fal.ai FLUX.2 [dev] Edit image-to-image editing generator.

Edit images using fal.ai's flux-2/edit model, enabling precise modifications
using natural language descriptions and hex color control.
Based on Black Forest Labs' FLUX.2 [dev] model.
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class Flux2EditImageSize(BaseModel):
    """Custom image size configuration."""

    width: int = Field(ge=512, le=2048, description="Image width (512-2048)")
    height: int = Field(ge=512, le=2048, description="Image height (512-2048)")


class Flux2EditInput(BaseModel):
    """Input schema for FLUX.2 [dev] Edit image editing.

    Artifact fields (like image_sources) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="Editing instruction (e.g., 'Change his clothes to casual suit and tie')"
    )
    image_sources: list[ImageArtifact] = Field(
        description="List of input images for editing (max 3 images)",
        min_length=1,
        max_length=3,
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of output images to generate (1-4)",
    )
    image_size: (
        Literal["square_hd", "portrait_4_3", "landscape_16_9"] | Flux2EditImageSize | None
    ) = Field(
        default=None,
        description=(
            "Output image size - predefined (square_hd, portrait_4_3, landscape_16_9) "
            "or custom dimensions"
        ),
    )
    acceleration: Literal["none", "regular", "high"] = Field(
        default="regular",
        description="Acceleration mode for generation speed/quality tradeoff",
    )
    num_inference_steps: int = Field(
        default=28,
        ge=4,
        le=50,
        description="Number of inference steps (4-50, higher = better quality but slower)",
    )
    output_format: Literal["jpeg", "png", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    guidance_scale: float = Field(
        default=2.5,
        ge=0.0,
        le=20.0,
        description="Guidance scale for generation (0-20)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible outputs",
    )
    enable_prompt_expansion: bool = Field(
        default=False,
        description="Enable automatic prompt expansion for better results",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter NSFW content",
    )
    sync_mode: bool = Field(
        default=False,
        description="If True, return data URI instead of URL (output won't be in request history)",
    )


class FalFlux2EditGenerator(BaseGenerator):
    """FLUX.2 [dev] Edit image-to-image generator using fal.ai."""

    name = "fal-flux-2-edit"
    artifact_type = "image"
    description = "Fal: FLUX.2 [dev] Edit - Precise image editing with natural language"

    def get_input_schema(self) -> type[Flux2EditInput]:
        return Flux2EditInput

    async def generate(
        self, inputs: Flux2EditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using fal.ai flux-2/edit model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalFlux2EditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal(inputs.image_sources, context)

        # Prepare arguments for fal.ai API
        arguments: dict[str, object] = {
            "prompt": inputs.prompt,
            "image_urls": image_urls,
            "num_images": inputs.num_images,
            "acceleration": inputs.acceleration,
            "num_inference_steps": inputs.num_inference_steps,
            "output_format": inputs.output_format,
            "guidance_scale": inputs.guidance_scale,
            "enable_prompt_expansion": inputs.enable_prompt_expansion,
            "enable_safety_checker": inputs.enable_safety_checker,
            "sync_mode": inputs.sync_mode,
        }

        # Add optional fields if provided
        if inputs.image_size is not None:
            if isinstance(inputs.image_size, str):
                arguments["image_size"] = inputs.image_size
            else:
                # Custom size object
                arguments["image_size"] = {
                    "width": inputs.image_size.width,
                    "height": inputs.image_size.height,
                }

        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/flux-2/edit",
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
            image_url_result = image_data.get("url")
            width = image_data.get("width", 1024)
            height = image_data.get("height", 1024)

            if not image_url_result:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Store with appropriate output_index
            artifact = await context.store_image_result(
                storage_url=image_url_result,
                format=inputs.output_format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: Flux2EditInput) -> float:
        """Estimate cost for FLUX.2 Edit generation.

        FLUX.2 [dev] Edit is a premium image editing model. Estimated cost
        is approximately $0.06 per image based on similar Flux models.
        """
        # Cost per image * number of images
        cost_per_image = 0.06
        return cost_per_image * inputs.num_images
