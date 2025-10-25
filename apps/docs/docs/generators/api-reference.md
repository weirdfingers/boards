# API Reference

Complete API reference for the Boards generators system, covering all classes, methods, and utilities.

## Core Classes

### BaseGenerator

Abstract base class for all generators in the Boards system.

```python
from boards.generators.base import BaseGenerator
```

#### Class Attributes

```python
class MyGenerator(BaseGenerator):
    name: str                    # Unique identifier for the generator
    artifact_type: str          # Type of artifact produced
    description: str            # Human-readable description
```

**name** (`str`, required)
: Unique string identifier for the generator (e.g., `"flux-pro"`, `"whisper"`)

**artifact_type** (`str`, required)
: Type of artifact this generator produces. Must be one of: `"image"`, `"video"`, `"audio"`, `"text"`, `"lora"`

**description** (`str`, required)
: Brief human-readable description of what the generator does

#### Required Methods

**get_input_schema()** → `Type[BaseModel]`
: Returns the Pydantic model class that defines the input schema for this generator.

```python
def get_input_schema(self) -> Type[BaseModel]:
    return MyInputClass
```

**generate(inputs: BaseModel)** → `BaseModel`
: Executes the generation process using the provided validated inputs.

```python
async def generate(self, inputs: BaseModel) -> BaseModel:
    # Implementation here
    return MyOutputClass(...)
```

**estimate_cost(inputs: BaseModel)** → `float`
: Estimates the cost of running this generation in USD.

```python
async def estimate_cost(self, inputs: BaseModel) -> float:
    return 0.05  # $0.05 USD
```

#### Optional Methods

**get_output_schema()** → `Type[BaseModel]`
: Returns the Pydantic model class that defines the output schema. Override if you need custom output schema definition.

```python
def get_output_schema(self) -> Type[BaseModel]:
    return MyOutputClass
```

#### Magic Methods

**__repr__()** → `str`
: String representation of the generator instance.

```python
>>> generator = FluxProGenerator()
>>> repr(generator)
'<FluxProGenerator(name=\'flux-pro\', type=\'image\')>'
```

## Artifact Types

### ImageArtifact

Represents generated or input images.

```python
from boards.generators.artifacts import ImageArtifact

artifact = ImageArtifact(
    generation_id="gen_123",
    storage_url="https://...",
    width=1024,
    height=1024,
    format="png"
)
```

#### Fields

**generation_id** (`str`, required)
: ID of the generation that created this artifact

**storage_url** (`str`, required)
: URL where the image file is stored

**width** (`int`, required)
: Image width in pixels

**height** (`int`, required)
: Image height in pixels

**format** (`str`, required)
: Image format (png, jpg, webp, gif, etc.)

#### Properties

```python
# Calculate aspect ratio
aspect_ratio = artifact.width / artifact.height

# Calculate megapixels
megapixels = (artifact.width * artifact.height) / 1_000_000
```

### VideoArtifact

Represents generated or input videos.

```python
from boards.generators.artifacts import VideoArtifact

artifact = VideoArtifact(
    generation_id="gen_456",
    storage_url="https://...",
    width=1920,
    height=1080,
    format="mp4",
    duration=30.5,    # Optional
    fps=30.0          # Optional
)
```

#### Required Fields

**generation_id** (`str`)
: Generation that created this video

**storage_url** (`str`)
: URL where video is stored

**width** (`int`)
: Video width in pixels

**height** (`int`)
: Video height in pixels

**format** (`str`)
: Video format (mp4, webm, mov, avi, etc.)

#### Optional Fields

**duration** (`Optional[float]`)
: Duration in seconds

**fps** (`Optional[float]`)
: Frames per second

#### Calculated Properties

```python
# Total frames (if duration and fps available)
if artifact.duration and artifact.fps:
    total_frames = artifact.duration * artifact.fps

# Resolution description
resolution = f"{artifact.width}x{artifact.height}"
```

### AudioArtifact

Represents generated or input audio files.

```python
from boards.generators.artifacts import AudioArtifact

artifact = AudioArtifact(
    generation_id="gen_789",
    storage_url="https://...",
    format="mp3",
    duration=120.0,      # Optional
    sample_rate=44100,   # Optional
    channels=2           # Optional
)
```

#### Required Fields

**generation_id** (`str`)
: Generation that created this audio

**storage_url** (`str`)
: URL where audio is stored

**format** (`str`)
: Audio format (mp3, wav, flac, ogg, m4a, etc.)

#### Optional Fields

**duration** (`Optional[float]`)
: Duration in seconds

**sample_rate** (`Optional[int]`)
: Sample rate in Hz (e.g., 44100, 48000)

**channels** (`Optional[int]`)
: Number of audio channels (1=mono, 2=stereo)

### TextArtifact

Represents generated or input text content.

```python
from boards.generators.artifacts import TextArtifact

artifact = TextArtifact(
    generation_id="gen_text",
    content="The generated text content...",
    format="plain"  # Optional, defaults to "plain"
)
```

#### Fields

**generation_id** (`str`, required)
: Generation that created this text

**content** (`str`, required)
: The actual text content

**format** (`str`, optional)
: Text format, defaults to "plain". Common values: `"plain"`, `"markdown"`, `"html"`, `"json"`, `"code"`, `"csv"`

#### Special Note

Unlike other artifacts, TextArtifact stores content directly. Use `artifact.content` to access the text, not `resolve_artifact()`.

```python
# Correct way to use text content
text_content = artifact.content

# Don't do this with TextArtifact
# file_path = await resolve_artifact(artifact)  # Will raise an error
```

### LoRArtifact

Represents LoRA (Low-Rank Adaptation) model files.

```python
from boards.generators.artifacts import LoRArtifact

artifact = LoRArtifact(
    generation_id="gen_lora",
    storage_url="https://...",
    base_model="stable-diffusion-v1-5",
    format="safetensors",
    trigger_words=["anime_style", "cel_shading"]  # Optional
)
```

#### Fields

**generation_id** (`str`, required)
: Generation that created this LoRA

**storage_url** (`str`, required)
: URL where LoRA file is stored

**base_model** (`str`, required)
: Base model this LoRA was trained on

**format** (`str`, required)
: File format (safetensors, ckpt, bin, etc.)

**trigger_words** (`Optional[list[str]]`)
: List of trigger words for this LoRA

## Registry System

### GeneratorRegistry

Central registry for managing generators.

```python
from boards.generators.registry import GeneratorRegistry, registry

# Use global instance
generator = registry.get("flux-pro")

# Or create your own
my_registry = GeneratorRegistry()
```

#### Methods

**register(generator: BaseGenerator)** → `None`
: Register a generator instance.

```python
registry.register(MyGenerator())

# Raises ValueError if generator name already registered
```

**get(name: str)** → `Optional[BaseGenerator]`
: Get generator by name, returns `None` if not found.

```python
generator = registry.get("flux-pro")
if generator:
    result = await generator.generate(inputs)
```

**list_all()** → `list[BaseGenerator]`
: Return all registered generators.

```python
all_generators = registry.list_all()
print(f"Total generators: {len(all_generators)}")
```

**list_by_artifact_type(artifact_type: str)** → `list[BaseGenerator]`
: Return generators that produce the specified artifact type.

```python
image_generators = registry.list_by_artifact_type("image")
video_generators = registry.list_by_artifact_type("video")
```

**list_names()** → `list[str]`
: Return list of all registered generator names.

```python
names = registry.list_names()
print("Available generators:", ", ".join(names))
```

**unregister(name: str)** → `bool`
: Remove generator by name. Returns `True` if found and removed.

```python
success = registry.unregister("old-generator")
if success:
    print("Generator removed")
```

**clear()** → `None`
: Remove all registered generators.

```python
registry.clear()
assert len(registry) == 0
```

#### Magic Methods

**__contains__(name: str)** → `bool`
: Check if generator with name is registered.

```python
if "flux-pro" in registry:
    print("FLUX Pro is available")
```

**__len__()** → `int`
: Return number of registered generators.

```python
print(f"Registry has {len(registry)} generators")
```

### Global Registry

The system provides a global registry instance:

```python
from boards.generators.registry import registry

# This is a singleton instance used throughout the system
assert registry is registry  # Same instance
```

## Artifact Resolution

### resolve_artifact()

Converts artifact references to local file paths for use with provider SDKs.

```python
from boards.generators.resolution import resolve_artifact

async def my_function(image_artifact: ImageArtifact):
    file_path = await resolve_artifact(image_artifact)
    # Now you can use file_path with any provider SDK
```

#### Parameters

**artifact** (`Union[AudioArtifact, VideoArtifact, ImageArtifact, LoRArtifact]`)
: Artifact to resolve to a local file path

#### Returns

**str**
: Local file path that can be used with provider SDKs

#### Raises

**ValueError**
: If trying to resolve a `TextArtifact` (use `.content` property instead)

**httpx.HTTPError**
: If downloading the artifact fails

#### Behavior

- If `storage_url` is already a local file path, returns it directly
- If `storage_url` is a remote URL, downloads to a temporary file and returns the path
- Handles file extensions based on the artifact's `format` field
- Cleans up temporary files on download failure

```python
# Example usage
async def process_image(image_artifact: ImageArtifact):
    try:
        image_path = await resolve_artifact(image_artifact)
        
        # Use with any provider SDK
        result = await some_sdk.process_image(image_path)
        
        return result
    except httpx.HTTPError as e:
        print(f"Failed to download image: {e}")
        raise
```

### Storage Functions

Functions for creating artifact instances from generated content.

#### store_image_result()

```python
from boards.generators.resolution import store_image_result

artifact = await store_image_result(
    storage_url="https://storage.com/image.png",
    format="png",
    generation_id="gen_123",
    width=1024,
    height=1024
)
```

**Parameters:**
- `storage_url` (`str`): URL where image is stored
- `format` (`str`): Image format
- `generation_id` (`str`): Generation that created this
- `width` (`int`): Image width in pixels
- `height` (`int`): Image height in pixels

**Returns:** `ImageArtifact`

#### store_video_result()

```python
from boards.generators.resolution import store_video_result

artifact = await store_video_result(
    storage_url="https://storage.com/video.mp4",
    format="mp4",
    generation_id="gen_456",
    width=1920,
    height=1080,
    duration=30.0,      # Optional
    fps=24.0           # Optional
)
```

**Parameters:**
- `storage_url` (`str`): URL where video is stored
- `format` (`str`): Video format
- `generation_id` (`str`): Generation that created this
- `width` (`int`): Video width in pixels
- `height` (`int`): Video height in pixels
- `duration` (`Optional[float]`): Duration in seconds
- `fps` (`Optional[float]`): Frames per second

**Returns:** `VideoArtifact`

#### store_audio_result()

```python
from boards.generators.resolution import store_audio_result

artifact = await store_audio_result(
    storage_url="https://storage.com/audio.mp3",
    format="mp3", 
    generation_id="gen_789",
    duration=120.0,     # Optional
    sample_rate=44100,  # Optional
    channels=2          # Optional
)
```

**Parameters:**
- `storage_url` (`str`): URL where audio is stored
- `format` (`str`): Audio format
- `generation_id` (`str`): Generation that created this
- `duration` (`Optional[float]`): Duration in seconds
- `sample_rate` (`Optional[int]`): Sample rate in Hz
- `channels` (`Optional[int]`): Number of channels

**Returns:** `AudioArtifact`

## Pydantic Integration

### Field Validation

Use Pydantic's field validation for input schemas:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Self

class ValidatedInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    quality: float = Field(ge=0.0, le=1.0)
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if 'forbidden' in v.lower():
            raise ValueError('Prompt contains forbidden content')
        return v.strip()
```

#### Common Field Constraints

**String Fields:**
```python
prompt: str = Field(
    min_length=1,           # Minimum length
    max_length=500,         # Maximum length  
    pattern=r"^[a-zA-Z\s]+$"  # Regex pattern
)
```

**Numeric Fields:**
```python
strength: float = Field(
    ge=0.0,        # Greater than or equal
    le=1.0,        # Less than or equal
    gt=0.0,        # Greater than (exclusive)
    lt=1.0         # Less than (exclusive)
)

steps: int = Field(
    ge=1,
    le=500,
    description="Number of inference steps"
)
```

**List Fields:**
```python
items: list[str] = Field(
    min_items=1,      # Minimum number of items
    max_items=10,     # Maximum number of items
    unique_items=True # All items must be unique
)
```

### Model Validators

Cross-field validation using model validators:

```python
from pydantic import model_validator

class ConditionalInput(BaseModel):
    mode: str
    text_input: Optional[str] = None
    image_input: Optional[ImageArtifact] = None
    
    @model_validator(mode='after') 
    def validate_conditional_fields(self) -> Self:
        if self.mode == "text" and not self.text_input:
            raise ValueError("text_input required when mode='text'")
        elif self.mode == "image" and not self.image_input:
            raise ValueError("image_input required when mode='image'")
        return self
```

### JSON Schema Generation

Generate JSON schemas for frontend integration:

```python
class MyInput(BaseModel):
    prompt: str = Field(description="Generation prompt")
    strength: float = Field(default=0.75, ge=0.0, le=1.0)

# Generate JSON schema
schema = MyInput.model_json_schema()

# Example output:
{
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "Generation prompt",
            "title": "Prompt"
        },
        "strength": {
            "type": "number",
            "default": 0.75,
            "maximum": 1.0,
            "minimum": 0.0,
            "title": "Strength"
        }
    },
    "required": ["prompt"],
    "title": "MyInput"
}
```

## Error Handling

### Common Error Patterns

```python
import os
from typing import Optional

class MyGenerator(BaseGenerator):
    async def generate(self, inputs: MyInput) -> MyOutput:
        # 1. Environment validation
        api_key = os.getenv("PROVIDER_API_KEY")
        if not api_key:
            raise ValueError(
                "PROVIDER_API_KEY environment variable is required. "
                "Get your key from https://provider.com/keys"
            )
        
        # 2. Provider-specific error handling
        try:
            result = await provider.generate(**inputs.dict())
        except provider.AuthenticationError:
            raise ValueError("Invalid API key - check PROVIDER_API_KEY")
        except provider.RateLimitError as e:
            retry_after = getattr(e, 'retry_after', 60)
            raise ValueError(f"Rate limited - retry after {retry_after} seconds")
        except provider.ValidationError as e:
            raise ValueError(f"Invalid input: {e.message}")
        except Exception as e:
            raise RuntimeError(f"Generation failed: {str(e)}")
        
        return MyOutput(...)
```

### Exception Types

The generators system uses these exception patterns:

**ValueError**
: For user-correctable errors (missing API keys, invalid inputs, provider validation errors)

**RuntimeError** 
: For unexpected errors that users can't directly fix

**httpx.HTTPError**
: For network/download errors when resolving artifacts

## Testing Utilities

### Mock Helpers

```python
from boards.generators.artifacts import ImageArtifact

def create_mock_image_artifact(
    generation_id: str = "test_gen",
    storage_url: str = "https://mock.com/image.png",
    width: int = 1024,
    height: int = 1024,
    format: str = "png"
) -> ImageArtifact:
    """Helper to create mock image artifacts for testing."""
    return ImageArtifact(
        generation_id=generation_id,
        storage_url=storage_url,
        width=width,
        height=height,
        format=format
    )
```

### Test Patterns

```python
import pytest
from unittest.mock import patch, AsyncMock

class TestMyGenerator:
    def setup_method(self):
        self.generator = MyGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        inputs = MyInput(prompt="test")
        
        with patch.dict(os.environ, {"API_KEY": "fake-key"}):
            with patch('provider.generate') as mock_gen:
                mock_gen.return_value = "result_url"
                
                with patch('my_generator.store_image_result') as mock_store:
                    mock_store.return_value = create_mock_image_artifact()
                    
                    result = await self.generator.generate(inputs)
                    assert isinstance(result, MyOutput)
```

## Type Hints

The generators system uses comprehensive type hints:

```python
from typing import Type, Optional, Union, List, Dict, Any
from pydantic import BaseModel
from boards.generators.base import BaseGenerator
from boards.generators.artifacts import ImageArtifact, VideoArtifact

class MyGenerator(BaseGenerator):
    def get_input_schema(self) -> Type[BaseModel]:
        # Returns a class, not an instance
        return MyInput
    
    async def generate(self, inputs: BaseModel) -> BaseModel:
        # inputs will be validated as MyInput type
        # Return type should match get_output_schema()
        return MyOutput(...)
    
    async def estimate_cost(self, inputs: BaseModel) -> float:
        # Always returns float (cost in USD)
        return 0.05
```

## Integration Points

### GraphQL Integration

Generators are automatically exposed via GraphQL:

```python
# Automatic schema generation
query GetGenerators($artifactType: String) {
  generators(artifactType: $artifactType) {
    name
    artifactType  
    description
    inputSchema    # JSON schema from Pydantic
    outputSchema   # JSON schema from Pydantic
  }
}

mutation RunGeneration($generatorName: String!, $inputs: JSON!) {
  runGeneration(generatorName: $generatorName, inputs: $inputs) {
    id
    status
    estimatedCost
    result {
      # Polymorphic result based on artifact_type
    }
  }
}
```

### Storage System Integration

Generators integrate with the pluggable storage system:

```python
# Storage functions will be implemented to:
# 1. Upload content to configured backend (S3, local, GCS, etc.)
# 2. Generate storage URLs
# 3. Handle metadata and thumbnails
# 4. Manage file lifecycle
```

### Database Integration

Generated artifacts are stored in the database with:

- Generation metadata (model, parameters, cost)
- Artifact relationships and lineage
- User permissions and board associations
- Audit trails and usage tracking

This API reference provides comprehensive coverage of all public interfaces in the Boards generators system.
