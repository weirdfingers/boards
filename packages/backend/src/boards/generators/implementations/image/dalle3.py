"""
DALL-E 3 generator using OpenAI API.

Demonstrates integration with OpenAI's SDK for image generation.
"""
from typing import Type
from pydantic import BaseModel, Field
import os

from ...base import BaseGenerator
from ...artifacts import ImageArtifact
from ...resolution import store_image_result
from ...registry import registry


class DallE3Input(BaseModel):
    """Input schema for DALL-E 3 image generation."""
    prompt: str = Field(description="Text prompt for image generation")
    size: str = Field(
        default="1024x1024",
        description="Image size",
        pattern="^(1024x1024|1024x1792|1792x1024)$"
    )
    quality: str = Field(
        default="standard", 
        description="Image quality",
        pattern="^(standard|hd)$"
    )
    style: str = Field(
        default="vivid",
        description="Image style", 
        pattern="^(vivid|natural)$"
    )


class DallE3Output(BaseModel):
    """Output schema for DALL-E 3 generation."""
    image: ImageArtifact


class DallE3Generator(BaseGenerator):
    """DALL-E 3 image generator using OpenAI API."""
    
    name = "dall-e-3"
    artifact_type = "image"
    description = "OpenAI's DALL-E 3 - advanced text-to-image generation"
    
    def get_input_schema(self) -> Type[DallE3Input]:
        return DallE3Input
    
    def get_output_schema(self) -> Type[DallE3Output]:
        return DallE3Output
    
    async def generate(self, inputs: DallE3Input) -> DallE3Output:
        """Generate image using OpenAI DALL-E 3."""
        # Check for API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Import SDK directly
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError:
            raise ValueError("openai package not installed. Run: pip install openai")
        
        client = AsyncOpenAI()
        
        # Use OpenAI SDK directly
        response = await client.images.generate(
            model="dall-e-3",
            prompt=inputs.prompt,
            size=inputs.size,
            quality=inputs.quality,
            style=inputs.style,
            n=1
        )
        
        # Get the generated image URL
        image_url = response.data[0].url
        
        # Parse dimensions from size
        width, height = map(int, inputs.size.split('x'))
        
        # Create artifact with the OpenAI URL
        image_artifact = await store_image_result(
            storage_url=image_url,
            format="png",  # DALL-E 3 outputs PNG
            generation_id="temp_gen_id",  # TODO: Get from context
            width=width,
            height=height
        )
        
        return DallE3Output(image=image_artifact)
    
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


# Register the generator
registry.register(DallE3Generator())