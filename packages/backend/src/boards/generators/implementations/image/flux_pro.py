"""
FLUX.1.1 Pro generator using Replicate API.

This demonstrates the simple pattern for creating generators:
1. Define Pydantic input/output models
2. Implement generation logic using provider SDK directly
3. Register with the global registry
"""

import os

from pydantic import BaseModel, Field

from ...artifacts import ImageArtifact
from ...base import BaseGenerator, GeneratorExecutionContext


class FluxProInput(BaseModel):
    """Input schema for FLUX.1.1 Pro image generation."""

    prompt: str = Field(description="Text prompt for image generation")
    aspect_ratio: str = Field(
        default="1:1",
        description="Image aspect ratio",
        pattern="^(1:1|16:9|21:9|2:3|3:2|4:5|5:4|9:16|9:21)$",
    )
    safety_tolerance: int = Field(
        default=2, ge=1, le=5, description="Safety tolerance level (1-5)"
    )


class FluxProOutput(BaseModel):
    """Output schema for FLUX.1.1 Pro generation."""

    image: ImageArtifact


class FluxProGenerator(BaseGenerator):
    """FLUX.1.1 Pro image generator using Replicate."""

    name = "flux-pro"
    artifact_type = "image"
    description = "FLUX.1.1 [pro] by Black Forest Labs - high-quality image generation"

    def get_input_schema(self) -> type[FluxProInput]:
        return FluxProInput

    def get_output_schema(self) -> type[FluxProOutput]:
        return FluxProOutput

    async def generate(
        self, inputs: FluxProInput, context: GeneratorExecutionContext
    ) -> FluxProOutput:
        """Generate image using Replicate FLUX.1.1 Pro model."""
        # Check for API key
        if not os.getenv("REPLICATE_API_TOKEN"):
            raise ValueError(
                "API configuration invalid. Missing REPLICATE_API_TOKEN environment variable."
            )

        # Import SDK directly - no wrapper layer
        try:
            import replicate  # type: ignore
        except ImportError as e:
            raise ValueError("Required dependencies not available") from e

        # Use Replicate SDK directly
        prediction = await replicate.async_run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": inputs.prompt,
                "aspect_ratio": inputs.aspect_ratio,
                "safety_tolerance": inputs.safety_tolerance,
            },
        )

        # prediction is a list with the output URL
        output_url = prediction[0] if isinstance(prediction, list) else prediction

        image_artifact = await context.store_image_result(
            storage_url=output_url,
            format="png",
            generation_id=context.generation_id,
            width=1024,
            height=1024,
        )

        return FluxProOutput(image=image_artifact)

    async def estimate_cost(self, inputs: FluxProInput) -> float:
        """Estimate cost for FLUX.1.1 Pro generation."""
        # FLUX.1.1 Pro typically costs around $0.055 per generation
        return 0.055
