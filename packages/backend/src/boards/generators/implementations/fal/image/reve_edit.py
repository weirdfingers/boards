"""
fal.ai Reve image editing generator.

Edit images using fal.ai's Reve edit model.
Allows uploading an existing image and transforming it through text prompts.

See: https://fal.ai/models/fal-ai/reve/edit
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ReveEditInput(BaseModel):
    """Input schema for Reve image editing.

    Artifact fields (like image_url) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="Text describing how to edit the image",
        min_length=1,
        max_length=2560,
    )
    image_url: ImageArtifact = Field(
        description="Reference image to edit (from a previous generation)",
    )
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate",
    )
    output_format: Literal["png", "jpeg", "webp"] = Field(
        default="png",
        description="Output image format",
    )
    sync_mode: bool = Field(
        default=False,
        description=(
            "If True, the media will be returned as a data URI and the output "
            "data won't be available in the request history"
        ),
    )


class FalReveEditGenerator(BaseGenerator):
    """Reve image editing generator using fal.ai."""

    name = "fal-reve-edit"
    artifact_type = "image"
    description = "Fal: Reve edit - AI-powered image editing and transformation"

    def get_input_schema(self) -> type[ReveEditInput]:
        return ReveEditInput

    async def generate(
        self, inputs: ReveEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using fal.ai Reve edit model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalReveEditGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        uploaded_image_url = image_urls[0]

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "image_url": uploaded_image_url,
            "num_images": inputs.num_images,
            "output_format": inputs.output_format,
            "sync_mode": inputs.sync_mode,
        }

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/reve/edit",
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
        #   "images": [{"url": "...", "width": ..., "height": ..., ...}, ...]
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

    async def estimate_cost(self, inputs: ReveEditInput) -> float:
        """Estimate cost for Reve edit generation.

        Reve edit pricing is $0.04 per image generated.
        """
        per_image_cost = 0.04
        return per_image_cost * inputs.num_images
