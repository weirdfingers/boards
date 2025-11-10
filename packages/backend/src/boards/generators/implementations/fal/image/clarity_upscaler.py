"""
fal.ai clarity-upscaler image upscaling generator.

Upscale images with high fidelity using fal.ai's clarity-upscaler model.
Supports upscaling factors from 1x to 4x with configurable creativity and resemblance.
"""

import os

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class ClarityUpscalerInput(BaseModel):
    """Input schema for clarity upscaler.

    Artifact fields (like image_url) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    image_url: ImageArtifact = Field(
        description="The input image to upscale (from a previous generation)"
    )
    prompt: str = Field(
        default="masterpiece, best quality, highres",
        description="Descriptive text guiding the upscaling generation",
    )
    upscale_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=4.0,
        description="Scaling multiplier for the upscaling (1-4x)",
    )
    negative_prompt: str = Field(
        default="(worst quality, low quality, normal quality:2)",
        description="Text describing unwanted details in the output",
    )
    creativity: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Deviation from prompt strength (0-1)",
    )
    resemblance: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="The strength of the ControlNet for fidelity to original (0-1)",
    )
    guidance_scale: float = Field(
        default=4.0,
        ge=0.0,
        le=20.0,
        description="CFG scale for prompt adherence (0-20)",
    )
    num_inference_steps: int = Field(
        default=18,
        ge=4,
        le=50,
        description="Number of processing iterations (4-50)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable content filtering",
    )


class FalClarityUpscalerGenerator(BaseGenerator):
    """Clarity upscaler generator using fal.ai."""

    name = "fal-clarity-upscaler"
    artifact_type = "image"
    description = "Fal: Clarity upscaler - High fidelity image upscaling (1-4x)"

    def get_input_schema(self) -> type[ClarityUpscalerInput]:
        return ClarityUpscalerInput

    async def generate(
        self, inputs: ClarityUpscalerInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Upscale images using fal.ai clarity-upscaler model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalClarityUpscalerGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image artifact to Fal's public storage
        # Fal API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Fal's temporary storage first
        from ..utils import upload_artifacts_to_fal

        # upload_artifacts_to_fal expects a list, so wrap the single image
        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        image_url = image_urls[0]  # Extract the single URL

        # Prepare arguments for fal.ai API
        arguments = {
            "image_url": image_url,
            "prompt": inputs.prompt,
            "upscale_factor": inputs.upscale_factor,
            "negative_prompt": inputs.negative_prompt,
            "creativity": inputs.creativity,
            "resemblance": inputs.resemblance,
            "guidance_scale": inputs.guidance_scale,
            "num_inference_steps": inputs.num_inference_steps,
            "enable_safety_checker": inputs.enable_safety_checker,
        }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/clarity-upscaler",
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
        #   "image": {"url": "...", "width": ..., "height": ...},
        #   "seed": 12345,
        #   "timings": {...}
        # }
        image_data = result.get("image")

        if not image_data:
            raise ValueError("No image returned from fal.ai API")

        image_url = image_data.get("url")
        if not image_url:
            raise ValueError("Image missing URL in fal.ai response")

        # Extract dimensions if available
        width = image_data.get("width")
        height = image_data.get("height")

        # If dimensions are not in the response, calculate from upscale factor
        if width is None or height is None:
            # Use original image dimensions multiplied by upscale factor
            original_width = inputs.image_url.width
            original_height = inputs.image_url.height
            if original_width and original_height:
                width = int(original_width * inputs.upscale_factor)
                height = int(original_height * inputs.upscale_factor)
            else:
                # Fallback to reasonable defaults
                width = 2048
                height = 2048

        # Store the upscaled image
        artifact = await context.store_image_result(
            storage_url=image_url,
            format="png",  # Clarity upscaler outputs PNG
            width=width,
            height=height,
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: ClarityUpscalerInput) -> float:
        """Estimate cost for clarity upscaler generation.

        Based on typical Fal image upscaling model pricing.
        """
        # Estimated cost per upscale operation
        # Using a conservative estimate based on similar Fal upscaling models
        return 0.05
