"""
fal.ai qwen-image text-to-image generator.

Qwen-Image is an advanced image generation model with exceptional text rendering
and precise editing capabilities. Based on Fal AI's fal-ai/qwen-image model.

See: https://fal.ai/models/fal-ai/qwen-image
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class LoraConfig(BaseModel):
    """LoRA configuration for model fine-tuning."""

    path: str = Field(description="Path or URL to LoRA weights")
    scale: float = Field(
        default=1.0,
        ge=0.0,
        le=4.0,
        description="Scale factor for LoRA influence (0-4)",
    )


class CustomImageSize(BaseModel):
    """Custom image dimensions."""

    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")


class QwenImageInput(BaseModel):
    """Input schema for qwen-image generation.

    Qwen-Image supports advanced text rendering and precise image editing capabilities.
    """

    prompt: str = Field(description="Text prompt for image generation")
    num_images: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (1-4)",
    )
    num_inference_steps: int = Field(
        default=30,
        ge=2,
        le=250,
        description="Number of inference steps (more steps = higher quality but slower)",
    )
    image_size: (
        Literal[
            "square_hd",
            "square",
            "portrait_4_3",
            "portrait_16_9",
            "landscape_4_3",
            "landscape_16_9",
        ]
        | CustomImageSize
    ) = Field(
        default="landscape_4_3",
        description="Image aspect ratio preset or custom dimensions",
    )
    output_format: Literal["jpeg", "png"] = Field(
        default="png",
        description="Output image format",
    )
    guidance_scale: float = Field(
        default=2.5,
        ge=0.0,
        le=20.0,
        description="Guidance scale for prompt adherence (0-20)",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (optional)",
    )
    negative_prompt: str = Field(
        default=" ",
        description="Negative prompt to specify unwanted elements",
    )
    acceleration: Literal["none", "regular", "high"] = Field(
        default="none",
        description="Acceleration level for faster generation",
    )
    enable_safety_checker: bool = Field(
        default=True,
        description="Enable safety checker to filter NSFW content",
    )
    use_turbo: bool = Field(
        default=False,
        description="Enable turbo mode for faster generation (10 steps, CFG=1.2)",
    )
    sync_mode: bool = Field(
        default=False,
        description="Use synchronous mode (wait for completion)",
    )
    loras: list[LoraConfig] = Field(
        default=[],
        max_length=3,
        description="LoRA configurations (up to 3 can be merged)",
    )


class FalQwenImageGenerator(BaseGenerator):
    """Qwen-Image generator using fal.ai.

    Advanced image generation with exceptional text rendering and editing capabilities.
    """

    name = "fal-qwen-image"
    artifact_type = "image"
    description = "Fal: Qwen-Image - advanced text-to-image with exceptional text rendering"

    def get_input_schema(self) -> type[QwenImageInput]:
        return QwenImageInput

    async def generate(
        self, inputs: QwenImageInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate images using fal.ai qwen-image model."""
        # Check for API key (fal-client uses FAL_KEY environment variable)
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalQwenImageGenerator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Prepare arguments for fal.ai API
        arguments = {
            "prompt": inputs.prompt,
            "num_images": inputs.num_images,
            "num_inference_steps": inputs.num_inference_steps,
            "output_format": inputs.output_format,
            "guidance_scale": inputs.guidance_scale,
            "negative_prompt": inputs.negative_prompt,
            "acceleration": inputs.acceleration,
            "enable_safety_checker": inputs.enable_safety_checker,
            "use_turbo": inputs.use_turbo,
            "sync_mode": inputs.sync_mode,
        }

        # Handle image_size: can be string or custom dimensions
        if isinstance(inputs.image_size, str):
            arguments["image_size"] = inputs.image_size
        else:
            # CustomImageSize object
            arguments["image_size"] = {
                "width": inputs.image_size.width,
                "height": inputs.image_size.height,
            }

        # Add seed if provided
        if inputs.seed is not None:
            arguments["seed"] = inputs.seed

        # Add LoRAs if provided
        if inputs.loras:
            arguments["loras"] = [{"path": lora.path, "scale": lora.scale} for lora in inputs.loras]

        # Submit async job and get handler
        handler = await fal_client.submit_async(
            "fal-ai/qwen-image",
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
            image_url = image_data.get("url")
            # Optional width and height
            width = image_data.get("width")
            height = image_data.get("height")

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

    async def estimate_cost(self, inputs: QwenImageInput) -> float:
        """Estimate cost for qwen-image generation.

        Qwen-image pricing is approximately $0.05 per image based on similar
        high-quality text-to-image models on fal.ai.
        """
        return 0.05 * inputs.num_images  # $0.05 per image, scaled by batch size
