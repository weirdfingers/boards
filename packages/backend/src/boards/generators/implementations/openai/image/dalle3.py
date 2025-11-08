"""
DALL-E 3 generator using OpenAI API.

Demonstrates integration with OpenAI's SDK for image generation.
"""

import os

from pydantic import BaseModel, Field

from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class DallE3Input(BaseModel):
    """Input schema for DALL-E 3 image generation."""

    prompt: str = Field(description="Text prompt for image generation")
    size: str = Field(
        default="1024x1024",
        description="Image size",
        pattern="^(1024x1024|1024x1792|1792x1024)$",
    )
    quality: str = Field(default="standard", description="Image quality", pattern="^(standard|hd)$")
    style: str = Field(default="vivid", description="Image style", pattern="^(vivid|natural)$")


class OpenAIDallE3Generator(BaseGenerator):
    """DALL-E 3 image generator using OpenAI API."""

    name = "openai-dall-e-3"
    artifact_type = "image"
    description = "OpenAI: DALL-E 3 - advanced text-to-image generation"

    def get_input_schema(self) -> type[DallE3Input]:
        return DallE3Input

    async def generate(
        self, inputs: DallE3Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate image using OpenAI DALL-E 3."""
        # Check for API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("API configuration invalid")

        # Import SDK directly
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI SDK is required for DallE3Generator. "
                "Install with: pip install weirdfingers-boards[generators-openai]"
            ) from e

        client = AsyncOpenAI()

        # Use OpenAI SDK directly
        response = await client.images.generate(
            model="dall-e-3",
            prompt=inputs.prompt,
            size=inputs.size,  # pyright: ignore[reportArgumentType]
            quality=inputs.quality,  # pyright: ignore[reportArgumentType]
            style=inputs.style,  # pyright: ignore[reportArgumentType]
            n=1,
        )

        # Get the generated image URL
        if not response.data or not response.data[0].url:
            raise ValueError("No image generated")
        image_url = response.data[0].url

        # Parse dimensions from size
        width, height = map(int, inputs.size.split("x"))

        # Store via context (downloads from OpenAI and uploads to our storage)
        image_artifact = await context.store_image_result(
            storage_url=image_url,
            format="png",  # DALL-E 3 outputs PNG
            width=width,
            height=height,
        )

        return GeneratorResult(outputs=[image_artifact])

    async def estimate_cost(self, inputs: DallE3Input) -> float:
        """Estimate cost for DALL-E 3 generation."""
        # DALL-E 3 pricing varies by quality and size
        if inputs.quality == "hd":
            if inputs.size in ["1024x1792", "1792x1024"]:
                return 0.080  # HD, non-square
            else:
                return 0.080  # HD, square
        else:  # standard quality
            if inputs.size in ["1024x1792", "1792x1024"]:
                return 0.040  # Standard, non-square
            else:
                return 0.040  # Standard, square
