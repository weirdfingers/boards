"""
FLUX.1.1 Pro generator using Replicate API.

This demonstrates the simple pattern for creating generators:
1. Define Pydantic input/output models
2. Implement generation logic using provider SDK directly
3. Register with the global registry
"""

import os
from collections.abc import AsyncIterator

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class FluxProInput(BaseModel):
    """Input schema for FLUX.1.1 Pro image generation."""

    prompt: str = Field(description="Text prompt for image generation")
    aspect_ratio: str = Field(
        default="1:1",
        description="Image aspect ratio",
        pattern="^(1:1|16:9|21:9|2:3|3:2|4:5|5:4|9:16|9:21)$",
    )
    safety_tolerance: int = Field(default=2, ge=1, le=5, description="Safety tolerance level (1-5)")


class ReplicateFluxProGenerator(BaseGenerator):
    """FLUX.1.1 Pro image generator using Replicate."""

    name = "replicate-flux-pro"
    artifact_type = "image"
    description = "Replicate: FLUX.1.1 [pro] by Black Forest Labs - high-quality image generation"

    def get_input_schema(self) -> type[FluxProInput]:
        return FluxProInput

    async def generate(
        self, inputs: FluxProInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate image using Replicate FLUX.1.1 Pro model."""
        # Check for API key
        if not os.getenv("REPLICATE_API_TOKEN"):
            raise ValueError("API configuration invalid. Missing REPLICATE_API_TOKEN")

        # Import SDK directly
        try:
            import replicate
            from replicate.helpers import FileOutput
        except ImportError as e:
            raise ImportError(
                "Replicate SDK is required for FluxProGenerator. "
                "Install with: pip install weirdfingers-boards[generators-replicate]"
            ) from e

        # Use Replicate SDK directly
        prediction: FileOutput | AsyncIterator[FileOutput] = await replicate.async_run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": inputs.prompt,
                "aspect_ratio": inputs.aspect_ratio,
                "safety_tolerance": inputs.safety_tolerance,
            },
        )

        # If prediction is an async iterator, get the first item; else, use as is.
        if isinstance(prediction, AsyncIterator):
            file_output = await anext(prediction)
        else:
            file_output = prediction

        output_url = file_output.url

        image_artifact = await context.store_image_result(
            storage_url=output_url,
            format="png",
            width=1024,
            height=1024,
        )

        return GeneratorResult(outputs=[image_artifact])

    async def estimate_cost(self, inputs: FluxProInput) -> float:
        """Estimate cost for FLUX.1.1 Pro generation."""
        # FLUX.1.1 Pro typically costs around $0.055 per generation
        return 0.055
