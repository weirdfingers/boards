# Getting Started with Generators

This guide will walk you through creating your first generator, from setup to testing. We'll build a simple text-to-image generator using Replicate's API.

## Prerequisites

Before you start, make sure you have:

- Boards development environment set up
- A Replicate API token ([get one here](https://replicate.com/account/api-tokens))
- Basic familiarity with Python and Pydantic

## Your First Generator

Let's create a generator that uses Stable Diffusion to generate images from text prompts.

### Step 1: Environment Setup

First, set your API key:

```bash
export REPLICATE_API_TOKEN="r8_your_token_here"
```

Or add it to your `.env` file:

```env
REPLICATE_API_TOKEN=r8_your_token_here
```

### Step 2: Create the Generator File

Create a new file at `packages/backend/src/boards/generators/implementations/image/stable_diffusion.py`:

```python
"""
Stable Diffusion generator using Replicate API.
"""
from typing import Type
from pydantic import BaseModel, Field

from ...base import BaseGenerator
from ...artifacts import ImageArtifact
from ...resolution import store_image_result
from ...registry import registry


class StableDiffusionInput(BaseModel):
    """Input schema for Stable Diffusion generation."""
    prompt: str = Field(
        description="Text description of the image to generate",
        min_length=1,
        max_length=500
    )
    negative_prompt: str = Field(
        default="",
        description="What to avoid in the generated image"
    )
    width: int = Field(
        default=512,
        description="Image width in pixels",
        ge=64,
        le=2048
    )
    height: int = Field(
        default=512, 
        description="Image height in pixels",
        ge=64,
        le=2048
    )
    num_inference_steps: int = Field(
        default=50,
        description="Number of denoising steps",
        ge=1,
        le=500
    )
    guidance_scale: float = Field(
        default=7.5,
        description="How closely to follow the prompt",
        ge=1.0,
        le=20.0
    )


class StableDiffusionOutput(BaseModel):
    """Output schema for Stable Diffusion generation."""
    image: ImageArtifact


class StableDiffusionGenerator(BaseGenerator):
    """Stable Diffusion image generator using Replicate."""
    
    name = "stable-diffusion"
    artifact_type = "image"
    description = "Stable Diffusion 1.5 - text-to-image generation with fine control"
    
    def get_input_schema(self) -> Type[StableDiffusionInput]:
        return StableDiffusionInput
    
    def get_output_schema(self) -> Type[StableDiffusionOutput]:
        return StableDiffusionOutput
    
    async def generate(self, inputs: StableDiffusionInput) -> StableDiffusionOutput:
        """Generate image using Stable Diffusion via Replicate."""
        import os
        import replicate
        
        # Check for API key
        if not os.getenv("REPLICATE_API_TOKEN"):
            raise ValueError(
                "REPLICATE_API_TOKEN environment variable is required. "
                "Get your token from https://replicate.com/account/api-tokens"
            )
        
        # Use Replicate SDK directly
        output = await replicate.async_run(
            "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
            input={
                "prompt": inputs.prompt,
                "negative_prompt": inputs.negative_prompt,
                "width": inputs.width,
                "height": inputs.height,
                "num_inference_steps": inputs.num_inference_steps,
                "guidance_scale": inputs.guidance_scale,
            }
        )
        
        # Replicate returns a list of URLs
        image_url = output[0] if isinstance(output, list) else output
        
        # Store result and create artifact
        image_artifact = await store_image_result(
            storage_url=image_url,
            format="png",
            generation_id="temp_gen_id",  # TODO: Get from generation context
            width=inputs.width,
            height=inputs.height
        )
        
        return StableDiffusionOutput(image=image_artifact)
    
    async def estimate_cost(self, inputs: StableDiffusionInput) -> float:
        """Estimate cost for Stable Diffusion generation."""
        # Stable Diffusion on Replicate costs about $0.0023 per image
        # Cost increases with more inference steps
        base_cost = 0.0023
        step_multiplier = inputs.num_inference_steps / 50  # 50 is the default
        return base_cost * step_multiplier


# Register the generator
registry.register(StableDiffusionGenerator())
```

### Step 3: Test Your Generator

Create a test file `packages/backend/tests/generators/implementations/test_stable_diffusion.py`:

```python
"""
Tests for StableDiffusionGenerator.
"""
import pytest
import os
from unittest.mock import patch

from boards.generators.implementations.image.stable_diffusion import (
    StableDiffusionGenerator,
    StableDiffusionInput,
    StableDiffusionOutput,
)


class TestStableDiffusionGenerator:
    def setup_method(self):
        self.generator = StableDiffusionGenerator()
    
    def test_generator_metadata(self):
        """Test generator has correct metadata."""
        assert self.generator.name == "stable-diffusion"
        assert self.generator.artifact_type == "image"
        assert "Stable Diffusion" in self.generator.description
    
    def test_input_validation(self):
        """Test input schema validation."""
        # Valid input
        valid_input = StableDiffusionInput(
            prompt="A beautiful sunset over mountains",
            width=768,
            height=768
        )
        assert valid_input.prompt == "A beautiful sunset over mountains"
        assert valid_input.width == 768
        
        # Invalid input (too large)
        with pytest.raises(ValueError):
            StableDiffusionInput(
                prompt="Test", 
                width=3000  # Too large
            )
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation.""" 
        inputs = StableDiffusionInput(
            prompt="A red apple",
            width=512,
            height=512
        )
        
        fake_output_url = "https://replicate.delivery/fake-image.png"
        
        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "fake-token"}):
            with patch('replicate.async_run') as mock_run:
                with patch('boards.generators.implementations.image.stable_diffusion.store_image_result') as mock_store:
                    # Mock Replicate response
                    mock_run.return_value = [fake_output_url]
                    
                    # Mock storage
                    from boards.generators.artifacts import ImageArtifact
                    mock_artifact = ImageArtifact(
                        generation_id="test",
                        storage_url=fake_output_url,
                        width=512,
                        height=512,
                        format="png"
                    )
                    mock_store.return_value = mock_artifact
                    
                    # Test generation
                    result = await self.generator.generate(inputs)
                    
                    assert isinstance(result, StableDiffusionOutput)
                    assert result.image == mock_artifact
                    
                    # Verify correct API call
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args
                    assert "stability-ai/stable-diffusion" in call_args[0][0]
                    assert call_args[1]["input"]["prompt"] == "A red apple"
    
    @pytest.mark.asyncio
    async def test_cost_estimation(self):
        """Test cost estimation."""
        inputs = StableDiffusionInput(prompt="Test", num_inference_steps=100)
        cost = await self.generator.estimate_cost(inputs)
        
        # Should be roughly double the base cost due to double the steps
        assert cost > 0.004  # More than base cost
        assert cost < 0.01   # But not too much
```

### Step 4: Run the Tests

```bash
cd packages/backend
python -m pytest tests/generators/implementations/test_stable_diffusion.py -v
```

### Step 5: Import Your Generator

To make your generator available to the system, import it in the image generators init file:

```python
# packages/backend/src/boards/generators/implementations/image/__init__.py
from . import flux_pro
from . import dalle3
from . import stable_diffusion  # Add this line
```

### Step 6: Verify Registration

You can verify your generator is registered:

```python
from boards.generators.registry import registry

# List all generators
print("All generators:", registry.list_names())

# Get your specific generator
sd_gen = registry.get("stable-diffusion")
print("Generator:", sd_gen.name, sd_gen.description)

# List image generators
image_gens = registry.list_by_artifact_type("image")
print(f"Image generators: {[g.name for g in image_gens]}")
```

## Understanding the Code

Let's break down what we built:

### Input Schema (StableDiffusionInput)
- **Validation**: Pydantic validates all inputs automatically
- **Constraints**: `min_length`, `ge` (greater/equal), `le` (less/equal) provide bounds
- **Descriptions**: Used for API documentation and UI generation
- **Defaults**: Fields can have sensible defaults

### Generator Class
- **Metadata**: Name, type, and description identify the generator
- **Schema Methods**: Define what inputs and outputs look like
- **Generation Logic**: Uses provider SDK directly, no wrappers
- **Cost Estimation**: Provides budget planning functionality

### Error Handling
- **Environment Checks**: Validates API keys early
- **Clear Messages**: Provides actionable error information
- **Provider Errors**: Could be enhanced to catch and translate provider-specific errors

## Frontend Integration

Once your generator is registered, the frontend automatically gets:

1. **TypeScript Types**: Generated from your Pydantic schemas
2. **Form UI**: Text inputs, number sliders, dropdowns based on field types
3. **Validation**: Client-side validation matching your schema
4. **Cost Display**: Shows estimated cost before generation

The form would look something like:

```typescript
// Auto-generated TypeScript interface
interface StableDiffusionInput {
  prompt: string;
  negative_prompt: string;
  width: number;    // Slider from 64 to 2048
  height: number;   // Slider from 64 to 2048  
  num_inference_steps: number;  // Slider from 1 to 500
  guidance_scale: number;       // Slider from 1.0 to 20.0
}
```

## Next Steps

Now that you have a working generator:

1. **Add More Validation**: Use Pydantic validators for complex rules
2. **Handle More Providers**: Try OpenAI, Fal.ai, or other services
3. **Create Artifact Chains**: Build generators that use other artifacts as inputs
4. **Add Comprehensive Tests**: Test edge cases, error conditions, and cost calculations
5. **Contribute Examples**: Share your generators with the community

## Common Patterns

### Environment Variable Validation
```python
def check_api_key(self, env_var: str, provider_name: str):
    if not os.getenv(env_var):
        raise ValueError(
            f"{env_var} environment variable is required. "
            f"Get your API key from {provider_name}"
        )
```

### Provider Error Translation
```python
try:
    result = await provider.generate(inputs)
except provider.AuthError:
    raise ValueError("Invalid API key")
except provider.RateLimitError as e:
    raise ValueError(f"Rate limited - retry in {e.retry_after}s")
```

### Dynamic Cost Calculation
```python
async def estimate_cost(self, inputs):
    base_cost = 0.001
    
    # More steps = higher cost
    step_factor = inputs.num_inference_steps / 50
    
    # Larger images = higher cost  
    size_factor = (inputs.width * inputs.height) / (512 * 512)
    
    return base_cost * step_factor * size_factor
```

You now have a fully functional generator integrated into the Boards system!
