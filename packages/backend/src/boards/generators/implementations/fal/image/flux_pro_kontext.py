"""
fal.ai FLUX.1 [pro] Kontext image-to-image generator.

Handles both text and reference images as inputs, enabling targeted local edits
and complex transformations of entire scenes using fal.ai's flux-pro/kontext model.
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class FluxProKontextInput(BaseModel):
    """Input schema for FLUX.1 [pro] Kontext image generation.

    Artifact fields (like image_url) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="Text prompt for image editing (e.g., 'Put a donut next to the flour')"
    )
    image_url: ImageArtifact = Field(
        description="Reference image for transformation (from previous generation)",
    )
    aspect_ratio: (
        Literal[
            "21:9",
            "16:9",
            "4:3",
            "3:2",
            "1:1",
            "2:3",
            "3:4",
            "9:16",
            "9:21",
        ]
        | None
    ) = Field(
        default=None,
        description="Image aspect ratio (optional)",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (1-4)",
    )
    output_format: Literal["jpeg", "png"] = Field(
        default="jpeg",
        description="Output image format",
    )
    sync_mode: bool = Field(
        default=False,
        description=(
            "If True, the media will be returned as a data URI and the output "
            "data won't be available in the request history"
        ),
    )
    safety_tolerance: str = Field(
        default="2",
        description="Safety tolerance level (1-6 scale, higher is more permissive)",
    )
    guidance_scale: float = Field(
        default=3.5,
        ge=1.0,
        le=20.0,
        description="Guidance scale for image generation (1-20)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible outputs (optional)",
    )
    enhance_prompt: bool = Field(
        default=False,
        description="Automatically enhance the prompt for better quality",
    )


class FalFluxProKontextGenerator(BaseGenerator):
    """FLUX.1 [pro] Kontext image-to-image generator using fal.ai."""

    name = "fal-flux-pro-kontext"
    artifact_type = "image"
    description = (
        "Fal: FLUX.1 [pro] Kontext - Image-to-image editing with text and reference images"
    )

    def get_input_schema(self) -> type[FluxProKontextInput]:
        return FluxProKontextInput

    async def generate(
        self, inputs: FluxProKontextInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai flux-pro/kontext model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalFluxProKontextGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        image_url = image_urls[0]  # Extract single URL from list

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": image_url,
            "num_images": inputs.num_images,
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
            "safety_tolerance": inputs.safety_tolerance,
            "guidance_scale": inputs.guidance_scale,
            "enhance_prompt": inputs.enhance_prompt,
        }

        # Add optional fields if provided
        if inputs.aspect_ratio is not None:
            arguments["aspect_ratio"] = inputs.aspect_ratio

        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/flux-pro/kontext",
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

    async def estimate_cost(self, inputs: FluxProKontextInput) -> float:
        """Estimate cost for FLUX.1 [pro] Kontext generation.

        FLUX.1 [pro] Kontext is a premium image-to-image model. Estimated cost
        is approximately $0.055 per image based on similar Flux Pro models.
        """
        # Cost per image * number of images
        cost_per_image = 0.055
        return cost_per_image * inputs.num_images
