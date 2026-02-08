"""
Bria RMBG 2.0 - Background Removal Generator.

Seamless removal of backgrounds from images, ideal for professional editing tasks.
Trained exclusively on licensed data for safe and risk-free commercial use.

Based on Fal AI's fal-ai/bria/background/remove model.
See: https://fal.ai/models/fal-ai/bria/background/remove
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class BriaBackgroundRemoveInput(BaseModel):
    """Input schema for Bria background removal.

    Artifact fields (like image_url) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    image_url: ImageArtifact = Field(description="Input image to remove background from")


class FalBriaBackgroundRemoveGenerator(BaseGenerator):
    """Bria RMBG 2.0 background removal generator using fal.ai."""

    name = "fal-bria-background-remove"
    artifact_type = "image"
    description = "Fal: Bria RMBG 2.0 - Seamless background removal from images"

    def get_input_schema(self) -> type[BriaBackgroundRemoveInput]:
        return BriaBackgroundRemoveInput

    async def generate(
        self, inputs: BriaBackgroundRemoveInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Remove background from image using fal.ai bria/background/remove model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalBriaBackgroundRemoveGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        image_url = image_urls[0]

        # Prepare arguments for fal.ai API
        arguments = {
            "image_url": image_url,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/bria/background/remove",
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

        # Extract image from result
        # fal.ai returns: {
        #   "image": {"url": "...", "width": ..., "height": ..., "content_type": ...}
        # }
        image_data = result.get("image")

        if not image_data:
            raise ValueError("No image returned from fal.ai API")

        output_url = image_data.get("url")
        if not output_url:
            raise ValueError("Image missing URL in fal.ai response")

        # Extract dimensions if available
        width = image_data.get("width")
        height = image_data.get("height")

        # If dimensions are not in the response, use original image dimensions
        if width is None or height is None:
            original_width = inputs.image_url.width
            original_height = inputs.image_url.height
            if original_width and original_height:
                width = original_width
                height = original_height
            else:
                # Fallback to reasonable defaults
                width = 1024
                height = 1024

        # Store the result image (background removal outputs PNG with transparency)
        artifact = await context.store_image_result(
            storage_url=output_url,
            format="png",
            width=width,
            height=height,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: BriaBackgroundRemoveInput) -> float:
        """Estimate cost for background removal.

        Based on typical Fal background removal model pricing.
        """
        # Estimated cost per background removal operation
        return 0.02
