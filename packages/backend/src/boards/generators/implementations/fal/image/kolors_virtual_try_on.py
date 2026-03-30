"""
Fal.ai Kolors Virtual Try-On generator.

A high quality image-based virtual try-on endpoint for commercial use.
Generates try-on results by processing human and garment images.

Based on Fal AI's fal-ai/kling/v1-5/kolors-virtual-try-on model.
See: https://fal.ai/models/fal-ai/kling/v1-5/kolors-virtual-try-on
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class KolorsVirtualTryOnInput(BaseModel):
    """Input schema for Kolors Virtual Try-On.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    human_image_url: ImageArtifact = Field(
        description="Image of the person to try on the garment",
    )
    garment_image_url: ImageArtifact = Field(
        description="Image of the garment to try on",
    )
    sync_mode: bool = Field(
        default=False,
        description="If true, the image will be returned in the response",
    )


class FalKolorsVirtualTryOnGenerator(BaseGenerator):
    """Generator for Kolors Virtual Try-On using fal.ai."""

    name = "fal-kolors-virtual-try-on"
    artifact_type = "image"
    description = "Fal: Kolors Virtual Try-On - High quality virtual clothing try-on"

    def get_input_schema(self) -> type[KolorsVirtualTryOnInput]:
        """Return the input schema for this generator."""
        return KolorsVirtualTryOnInput

    async def generate(
        self, inputs: KolorsVirtualTryOnInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate virtual try-on image using fal.ai kling/v1-5/kolors-virtual-try-on."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalKolorsVirtualTryOnGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        from ..utils import upload_artifacts_to_fal

        human_image_urls = await upload_artifacts_to_fal([inputs.human_image_url], context)
        garment_image_urls = await upload_artifacts_to_fal([inputs.garment_image_url], context)

        human_image_url = human_image_urls[0]
        garment_image_url = garment_image_urls[0]

        # Prepare arguments for fal.ai API
        arguments = {
            "human_image_url": human_image_url,
            "garment_image_url": garment_image_url,
            "sync_mode": inputs.sync_mode,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "fal-ai/kling/v1-5/kolors-virtual-try-on",
            arguments=arguments,
        )

        # Store external job ID
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

        # Extract output image from result
        # API returns: {"image": {"url": "...", "width": ..., "height": ...}}
        image_data = result.get("image")
        if not image_data:
            raise ValueError("No image returned from fal.ai API")

        image_url = image_data.get("url")
        if not image_url:
            raise ValueError("Image missing URL in fal.ai response")

        width = image_data.get("width", 768)
        height = image_data.get("height", 1024)

        # Determine format from content_type or default to png
        content_type = image_data.get("content_type", "image/png")
        if "jpeg" in content_type or "jpg" in content_type:
            format_str = "jpeg"
        else:
            format_str = "png"

        # Store the result
        artifact = await context.store_image_result(
            storage_url=image_url,
            format=format_str,
            width=width,
            height=height,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: KolorsVirtualTryOnInput) -> float:
        """Estimate cost for Kolors Virtual Try-On generation.

        Pricing not specified in documentation, estimated at ~$0.05 per generation
        based on similar image processing models.
        """
        return 0.05
