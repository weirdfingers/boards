# Generators API Reference

This document provides detailed API reference for the Boards generators system.

## Core Classes

### BaseGenerator

Abstract base class for all generators.

```python
from boards.generators.base import BaseGenerator

class MyGenerator(BaseGenerator):
    name: str                    # Unique identifier for the generator
    artifact_type: str          # Type of artifact produced ('image', 'video', 'audio', 'text', 'lora')  
    description: str            # Human-readable description
    
    def get_input_schema(self) -> Type[BaseModel]:
        """Return Pydantic model class for input validation."""
        pass
    
    async def generate(self, inputs: BaseModel) -> BaseModel:
        """Execute generation and return results."""
        pass
    
    async def estimate_cost(self, inputs: BaseModel) -> float:
        """Estimate cost in USD for this generation."""
        pass
    
    def get_output_schema(self) -> Type[BaseModel]:
        """Return Pydantic model class for output (optional override)."""
        pass
```

#### Required Attributes

- **`name`**: Unique string identifier (e.g., `"flux-pro"`, `"whisper"`)
- **`artifact_type`**: One of `"image"`, `"video"`, `"audio"`, `"text"`, `"lora"`
- **`description`**: Brief description of what the generator does

#### Required Methods

- **`get_input_schema()`**: Return the Pydantic model class that defines valid inputs
- **`generate(inputs)`**: Core generation logic that produces artifacts
- **`estimate_cost(inputs)`**: Return estimated cost in USD as a float

## Artifact Types

### ImageArtifact

Represents generated or input images.

```python
from boards.generators.artifacts import ImageArtifact

artifact = ImageArtifact(
    generation_id="gen_123",        # ID of generation that created this
    storage_url="https://...",      # URL where image is stored  
    width=1024,                     # Image width in pixels
    height=1024,                    # Image height in pixels
    format="png"                    # Image format (png, jpg, webp, etc.)
)
```

### VideoArtifact

Represents generated or input videos.

```python
from boards.generators.artifacts import VideoArtifact

artifact = VideoArtifact(
    generation_id="gen_456",        # Required: generation ID
    storage_url="https://...",      # Required: storage location
    width=1920,                     # Required: video width
    height=1080,                    # Required: video height  
    format="mp4",                   # Required: video format
    duration=60.5,                  # Optional: duration in seconds
    fps=30.0                        # Optional: frames per second
)
```

### AudioArtifact

Represents generated or input audio.

```python
from boards.generators.artifacts import AudioArtifact

artifact = AudioArtifact(
    generation_id="gen_789",        # Required: generation ID
    storage_url="https://...",      # Required: storage location
    format="mp3",                   # Required: audio format
    duration=120.0,                 # Optional: duration in seconds
    sample_rate=44100,              # Optional: sample rate in Hz
    channels=2                      # Optional: number of channels
)
```

### TextArtifact

Represents generated or input text.

```python
from boards.generators.artifacts import TextArtifact

artifact = TextArtifact(
    generation_id="gen_text",       # Required: generation ID
    content="Generated text...",    # Required: the actual text content
    format="plain"                  # Optional: format (plain, markdown, html)
)
```

### LoRArtifact

Represents LoRA (Low-Rank Adaptation) models.

```python
from boards.generators.artifacts import LoRArtifact

artifact = LoRArtifact(
    generation_id="gen_lora",       # Required: generation ID
    storage_url="https://...",      # Required: storage location
    base_model="sd-v1.5",          # Required: base model name
    format="safetensors",           # Required: file format
    trigger_words=["style1", "tag"] # Optional: trigger words list
)
```

## Generator Registry

### Global Registry

The system provides a global registry for managing generators:

```python
from boards.generators.registry import registry

# Register a generator
generator_instance = MyGenerator()
registry.register(generator_instance)

# Get a generator by name
generator = registry.get("my-generator")

# List all generators
all_generators = registry.list_all()

# List generators by artifact type
image_generators = registry.list_by_artifact_type("image")

# Check if generator exists
if "my-generator" in registry:
    print("Generator is registered")

# Get count of registered generators
count = len(registry)
```

### GeneratorRegistry Methods

```python
class GeneratorRegistry:
    def register(self, generator: BaseGenerator) -> None:
        """Register a generator instance."""
    
    def get(self, name: str) -> Optional[BaseGenerator]:
        """Get generator by name, returns None if not found."""
    
    def list_all(self) -> List[BaseGenerator]:
        """Return all registered generators."""
    
    def list_by_artifact_type(self, artifact_type: str) -> List[BaseGenerator]:
        """Return generators that produce the specified artifact type."""
    
    def list_names(self) -> List[str]:
        """Return list of all registered generator names."""
    
    def unregister(self, name: str) -> bool:
        """Remove generator by name. Returns True if found and removed."""
    
    def clear(self) -> None:
        """Remove all registered generators."""
    
    def __contains__(self, name: str) -> bool:
        """Check if generator with name is registered."""
    
    def __len__(self) -> int:
        """Return number of registered generators."""
```

## Artifact Resolution

### resolve_artifact()

Converts artifact references to local file paths for use with provider SDKs:

```python
from boards.generators.resolution import resolve_artifact

async def generate(self, inputs):
    # Resolve artifacts to local file paths
    audio_path = await resolve_artifact(inputs.audio_source)
    video_path = await resolve_artifact(inputs.video_source)
    
    # Now you can pass file paths to any provider SDK
    result = await provider.process(audio=audio_path, video=video_path)
```

**Supported artifacts**: `AudioArtifact`, `VideoArtifact`, `ImageArtifact`, `LoRArtifact`

**Not supported**: `TextArtifact` (use `.content` property directly)

### Store Result Functions

Create artifact instances from generated content:

```python
from boards.generators.resolution import (
    store_image_result,
    store_video_result, 
    store_audio_result
)

# Store generated image
image_artifact = await store_image_result(
    storage_url="https://storage.com/image.png",
    format="png",
    generation_id="gen_123",
    width=1024,
    height=1024
)

# Store generated video  
video_artifact = await store_video_result(
    storage_url="https://storage.com/video.mp4",
    format="mp4", 
    generation_id="gen_456",
    width=1920,
    height=1080,
    duration=60.0,      # Optional
    fps=30.0           # Optional  
)

# Store generated audio
audio_artifact = await store_audio_result(
    storage_url="https://storage.com/audio.mp3",
    format="mp3",
    generation_id="gen_789", 
    duration=120.0,     # Optional
    sample_rate=44100,  # Optional
    channels=2          # Optional
)
```

## Pydantic Integration

### Input Schema Patterns

#### Basic Inputs

```python
from pydantic import BaseModel, Field

class BasicInput(BaseModel):
    prompt: str = Field(description="Text prompt")
    strength: float = Field(default=0.75, ge=0.0, le=1.0, description="Generation strength")
    seed: Optional[int] = Field(None, description="Random seed")
```

#### Artifact Inputs

```python
class ArtifactInput(BaseModel):
    image_source: ImageArtifact = Field(description="Input image")
    audio_source: AudioArtifact = Field(description="Input audio")
    reference_text: TextArtifact = Field(description="Reference text")
```

#### Validation and Constraints

```python
from pydantic import field_validator

class ValidatedInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    quality: str = Field(pattern="^(low|medium|high)$")
    dimensions: str = Field(pattern="^\\d+x\\d+$")
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v):
        if 'forbidden' in v.lower():
            raise ValueError('Prompt contains forbidden content')
        return v.strip()
```

#### Conditional Fields

```python
class ConditionalInput(BaseModel):
    mode: str = Field(pattern="^(text|image)$")
    text_prompt: Optional[str] = Field(None)
    image_prompt: Optional[ImageArtifact] = Field(None)
    
    @model_validator(mode='after')
    def validate_conditional_fields(self):
        if self.mode == 'text' and not self.text_prompt:
            raise ValueError('text_prompt required when mode=text')
        elif self.mode == 'image' and not self.image_prompt:
            raise ValueError('image_prompt required when mode=image')
        return self
```

### Output Schema Patterns

#### Simple Outputs

```python
class SimpleOutput(BaseModel):
    result: ImageArtifact
    metadata: dict = Field(default_factory=dict)
```

#### Multiple Artifacts

```python  
class MultiOutput(BaseModel):
    images: List[ImageArtifact] = Field(description="Generated images")
    preview: ImageArtifact = Field(description="Low-res preview")
    generation_time: float = Field(description="Time taken in seconds")
```

## JSON Schema Generation

Pydantic models automatically generate JSON schemas for frontend integration:

```python
# Get JSON schema for frontend type generation
schema = MyInputClass.model_json_schema()

# Example output:
{
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string", 
            "description": "Text prompt",
            "minLength": 1,
            "maxLength": 500
        },
        "strength": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 0.75,
            "description": "Generation strength"
        }
    },
    "required": ["prompt"]
}
```

## Error Handling

### Common Error Patterns

```python
async def generate(self, inputs):
    # Check environment variables
    api_key = os.getenv("PROVIDER_API_KEY")
    if not api_key:
        raise ValueError(
            "PROVIDER_API_KEY environment variable required. "
            "Get your key from https://provider.com/keys"
        )
    
    # Provider-specific error handling
    try:
        result = await provider.generate(inputs)
    except provider.AuthenticationError:
        raise ValueError("Invalid API key - check PROVIDER_API_KEY")
    except provider.RateLimitError as e:
        raise ValueError(f"Rate limited - retry after {e.retry_after} seconds")
    except provider.ValidationError as e:
        raise ValueError(f"Invalid input: {e.message}")
    except Exception as e:
        raise RuntimeError(f"Generation failed: {str(e)}")
```

### Best Practices

1. **Specific Error Messages**: Provide actionable error messages
2. **Environment Variable Checks**: Validate required configuration early
3. **Provider Error Translation**: Convert provider errors to user-friendly messages
4. **Resource Cleanup**: Clean up temporary files in finally blocks

## Testing

### Generator Testing Pattern

```python
import pytest
from unittest.mock import patch, AsyncMock

class TestMyGenerator:
    def setup_method(self):
        self.generator = MyGenerator()
    
    def test_metadata(self):
        assert self.generator.name == "my-generator"
        assert self.generator.artifact_type == "image"
    
    def test_input_schema(self):
        schema_class = self.generator.get_input_schema()
        assert schema_class == MyInputClass
        
        # Test schema validation
        valid_input = schema_class(prompt="test")
        assert valid_input.prompt == "test"
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        inputs = MyInputClass(prompt="test prompt")
        
        with patch.dict(os.environ, {"API_KEY": "fake-key"}):
            with patch('provider.generate') as mock_generate:
                mock_generate.return_value = "fake_result_url"
                
                result = await self.generator.generate(inputs)
                
                assert isinstance(result, MyOutputClass)
                mock_generate.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_generate_missing_api_key(self):
        inputs = MyInputClass(prompt="test")
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API_KEY.*required"):
                await self.generator.generate(inputs)
    
    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        inputs = MyInputClass(prompt="short")
        cost = await self.generator.estimate_cost(inputs)
        
        assert isinstance(cost, float)
        assert cost > 0
```

## Integration Points

### Storage System Integration

Generators integrate with the Boards storage system through the resolution utilities:

```python
# The store_*_result functions will be implemented to:
# 1. Upload content to configured storage backend (S3, local, etc.)  
# 2. Return artifact with proper storage_url
# 3. Handle metadata and thumbnails
```

### Database Integration

Generated artifacts are automatically stored in the database with:

- Generation metadata (model, parameters, cost)
- Artifact metadata (dimensions, duration, format)
- Relationships to boards and users
- Audit trail information

### GraphQL API Integration

Registered generators are automatically exposed via GraphQL:

```graphql
query GetGenerators($artifactType: String) {
  generators(artifactType: $artifactType) {
    name
    artifactType
    description
    inputSchema  # JSON schema for frontend
  }
}

mutation RunGeneration($generatorName: String!, $inputs: JSON!) {
  runGeneration(generatorName: $generatorName, inputs: $inputs) {
    id
    status
    result {
      ... on ImageArtifact {
        storageUrl
        width
        height
      }
    }
  }
}
```
