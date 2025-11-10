"""
fal.ai Crystal Upscaler - Advanced image enhancement for facial details and portraits.

Upscales images with specialized enhancement for facial details using Clarity AI's
upscaling technology. Supports scale factors from 1x to 200x.

Based on Fal AI's fal-ai/crystal-upscaler model.
See: https://fal.ai/models/fal-ai/crystal-upscaler
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class CrystalUpscalerInput(BaseModel):
    """Input schema for crystal-upscaler.

    Artifact fields (like image_url) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    image_url: ImageArtifact = Field(
        description="Input image to upscale (from a previous generation)"
    )
    scale_factor: int = Field(
        default=2,
        ge=1,
        le=200,
        description="Scale factor for upscaling (1-200)",
    )


class FalCrystalUpscalerGenerator(BaseGenerator):
    """Crystal Upscaler generator using fal.ai."""

    name = "fal-crystal-upscaler"
    artifact_type = "image"
    description = "Fal: Crystal Upscaler - Advanced image enhancement for facial details"

    def get_input_schema(self) -> type[CrystalUpscalerInput]:
        return CrystalUpscalerInput

    async def generate(
        self, inputs: CrystalUpscalerInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Upscale image using fal.ai crystal-upscaler model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalCrystalUpscalerGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        # upload_artifacts_to_fal expects a list, returns a list
        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        image_url = image_urls[0]

        # Prepare arguments for fal.ai API
        arguments = {
            "image_url": image_url,
            "scale_factor": inputs.scale_factor,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/crystal-upscaler",
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
        #   "images": [{"url": "...", "width": ..., "height": ..., ...}]
        # }
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from fal.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            image_url = image_data.get("url")
            # Extract dimensions from response
            width = image_data.get("width")
            height = image_data.get("height")

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in fal.ai response")

            # Determine format from content_type or use png as default
            content_type = image_data.get("content_type", "image/png")
            format_map = {
                "image/jpeg": "jpeg",
                "image/jpg": "jpeg",
                "image/png": "png",
                "image/webp": "webp",
            }
            format = format_map.get(content_type, "png")

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

    async def estimate_cost(self, inputs: CrystalUpscalerInput) -> float:
        """Estimate cost for crystal upscaler generation.

        Using a conservative estimate for image upscaling operations.
        Actual cost may vary based on image size and scale factor.
        """
        # Base cost per upscale operation
        # Higher scale factors may cost more, but using fixed cost for now
        base_cost = 0.05
        return base_cost
