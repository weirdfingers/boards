# Adding Generators to Boards

This guide explains how to create and add new generators to the Boards system. Generators are components that integrate AI generation services and define their input/output schemas using Pydantic models.

## Quick Start

Creating a new generator involves just 3 steps:

1. **Define input/output schemas** using Pydantic models
2. **Implement the generator class** with generation logic  
3. **Register the generator** with the system

## Example: Creating a Text-to-Speech Generator

Let's create a generator that converts text to speech using ElevenLabs API:

### Step 1: Define Pydantic Schemas

```python
from typing import Type, Optional
from pydantic import BaseModel, Field
from boards.generators.base import BaseGenerator
from boards.generators.artifacts import TextArtifact, AudioArtifact

class TTSInput(BaseModel):
    """Input schema for text-to-speech generation."""
    text_source: TextArtifact = Field(description="Text to convert to speech")
    voice_id: str = Field(description="Voice ID to use for generation")
    stability: float = Field(default=0.75, ge=0.0, le=1.0, description="Voice stability")
    clarity: float = Field(default=0.75, ge=0.0, le=1.0, description="Voice clarity")

class TTSOutput(BaseModel):
    """Output schema for text-to-speech generation."""
    audio: AudioArtifact
```

### Step 2: Implement Generator Class

```python
import os
from boards.generators.resolution import store_audio_result

class ElevenLabsTTSGenerator(BaseGenerator):
    """Text-to-speech generator using ElevenLabs API."""
    
    name = "elevenlabs-tts"
    artifact_type = "audio" 
    description = "ElevenLabs text-to-speech generation"
    
    def get_input_schema(self) -> Type[TTSInput]:
        return TTSInput
    
    def get_output_schema(self) -> Type[TTSOutput]:
        return TTSOutput
    
    async def generate(self, inputs: TTSInput) -> TTSOutput:
        """Generate speech from text using ElevenLabs."""
        # Check for API key
        if not os.getenv("ELEVENLABS_API_KEY"):
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
        
        # Import SDK directly - no wrapper layer
        import elevenlabs
        
        # Get text content from the text artifact
        text_content = inputs.text_source.content
        
        # Use ElevenLabs SDK directly
        audio_bytes = elevenlabs.generate(
            text=text_content,
            voice=inputs.voice_id,
            model="eleven_monolingual_v1",
            voice_settings=elevenlabs.VoiceSettings(
                stability=inputs.stability,
                similarity_boost=inputs.clarity
            )
        )
        
        # TODO: In real implementation, upload to storage and get URL
        storage_url = "https://storage.example.com/generated_audio.mp3"
        
        # Create audio artifact
        audio_artifact = await store_audio_result(
            storage_url=storage_url,
            format="mp3",
            generation_id="temp_gen_id",  # TODO: Get from generation context
            duration=None,  # Could estimate from text length
            sample_rate=22050,
            channels=1
        )
        
        return TTSOutput(audio=audio_artifact)
    
    async def estimate_cost(self, inputs: TTSInput) -> float:
        """Estimate cost based on text length."""
        text_length = len(inputs.text_source.content)
        # ElevenLabs charges per character, roughly $0.0001 per character
        return text_length * 0.0001
```

### Step 3: Register the Generator

```python
from boards.generators.registry import registry

# Register the generator so it's available to the system
registry.register(ElevenLabsTTSGenerator())
```

## Key Concepts

### Artifact Types

Artifacts represent generated content and can be used as inputs to other generators:

- **`ImageArtifact`**: Images (PNG, JPG, WebP, etc.)
- **`VideoArtifact`**: Videos (MP4, WebM, etc.) 
- **`AudioArtifact`**: Audio files (MP3, WAV, etc.)
- **`TextArtifact`**: Text content (plain, markdown, HTML, etc.)
- **`LoRArtifact`**: LoRA models (SafeTensors, etc.)

### Artifact Resolution

The system automatically resolves artifact references to file paths:

```python
# If input has an artifact, resolve it to a usable file path
audio_file_path = await resolve_artifact(inputs.audio_source)

# Now you can pass the file path to any provider SDK
result = await some_api.process_audio(audio_file_path)
```

For `TextArtifact`, use the `.content` property directly:

```python
# Text artifacts contain content directly
text_content = inputs.text_source.content
```

### Environment Variables

Generators should use environment variables for API keys and configuration:

```python
import os

# Check for required environment variables
if not os.getenv("PROVIDER_API_KEY"):
    raise ValueError("PROVIDER_API_KEY environment variable is required")
```

## Advanced Examples

### Multiple Input Artifacts

Some generators need multiple artifacts as input:

```python
class VideoWithMusicInput(BaseModel):
    """Add background music to a video."""
    video_source: VideoArtifact = Field(description="Video to add music to")
    audio_source: AudioArtifact = Field(description="Background music")
    music_volume: float = Field(default=0.3, ge=0.0, le=1.0, description="Music volume")

async def generate(self, inputs: VideoWithMusicInput) -> VideoWithMusicOutput:
    # Resolve both artifacts
    video_path = await resolve_artifact(inputs.video_source)
    audio_path = await resolve_artifact(inputs.audio_source)
    
    # Use both files with your provider SDK
    result = await provider.add_background_music(
        video=video_path,
        audio=audio_path,
        volume=inputs.music_volume
    )
    
    return VideoWithMusicOutput(video=result_artifact)
```

### Custom Validation

Use Pydantic validators for complex input validation:

```python
from pydantic import field_validator

class CustomInput(BaseModel):
    prompt: str
    style: str
    
    @field_validator('style')
    @classmethod
    def validate_style(cls, v):
        allowed_styles = ['realistic', 'artistic', 'cartoon']
        if v not in allowed_styles:
            raise ValueError(f'Style must be one of {allowed_styles}')
        return v
```

### Conditional Fields

Some inputs might be conditional on other fields:

```python
from typing import Union
from pydantic import Field

class ConditionalInput(BaseModel):
    input_type: str = Field(description="Type of input", pattern="^(text|image)$")
    text_input: Optional[str] = Field(None, description="Text input (if input_type=text)")
    image_input: Optional[ImageArtifact] = Field(None, description="Image input (if input_type=image)")
    
    def model_validate(cls, values):
        input_type = values.get('input_type')
        if input_type == 'text' and not values.get('text_input'):
            raise ValueError('text_input is required when input_type=text')
        elif input_type == 'image' and not values.get('image_input'):
            raise ValueError('image_input is required when input_type=image')
        return values
```

## Testing Your Generator

Create comprehensive tests for your generator:

```python
import pytest
from unittest.mock import patch, AsyncMock

class TestElevenLabsTTSGenerator:
    def setup_method(self):
        self.generator = ElevenLabsTTSGenerator()
    
    def test_generator_metadata(self):
        assert self.generator.name == "elevenlabs-tts"
        assert self.generator.artifact_type == "audio"
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        input_data = TTSInput(
            text_source=TextArtifact(
                generation_id="test",
                content="Hello world"
            ),
            voice_id="voice_123"
        )
        
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "fake-key"}):
            with patch('elevenlabs.generate') as mock_generate:
                mock_generate.return_value = b"fake audio bytes"
                
                result = await self.generator.generate(input_data)
                
                assert isinstance(result, TTSOutput)
                assert isinstance(result.audio, AudioArtifact)
```

## Best Practices

### 1. Use Provider SDKs Directly

Don't create wrapper layers - import and use provider SDKs directly:

```python
# Good: Use SDK directly  
import replicate
result = await replicate.async_run("model", input=data)

# Avoid: Creating unnecessary wrappers
class ReplicateWrapper:
    def __init__(self): ...
```

### 2. Handle Errors Gracefully

Provide clear error messages for common issues:

```python
async def generate(self, inputs):
    if not os.getenv("API_KEY"):
        raise ValueError(
            "API_KEY environment variable is required. "
            "Get your key from https://provider.com/api-keys"
        )
    
    try:
        result = await provider_api.generate(inputs)
    except provider_api.AuthError:
        raise ValueError("Invalid API key - check your API_KEY environment variable")
    except provider_api.RateLimitError:
        raise ValueError("Rate limit exceeded - please try again later")
```

### 3. Accurate Cost Estimation

Implement realistic cost estimation:

```python
async def estimate_cost(self, inputs: MyInput) -> float:
    # Base cost
    base_cost = 0.01
    
    # Variable costs based on input complexity
    if inputs.high_quality:
        base_cost *= 2
    
    # Consider input size
    if hasattr(inputs, 'image_input'):
        # Larger images might cost more
        pixels = inputs.image_input.width * inputs.image_input.height
        base_cost += (pixels / 1000000) * 0.005  # $0.005 per megapixel
    
    return base_cost
```

### 4. Comprehensive Input Validation

Use Pydantic's full validation capabilities:

```python
class WellValidatedInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000, description="Generation prompt")
    strength: float = Field(ge=0.0, le=1.0, description="Generation strength")
    seed: Optional[int] = Field(None, ge=0, description="Random seed for reproducibility")
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Prompt cannot be empty or only whitespace')
        return v.strip()
```

## Deployment and Registration

### Auto-Registration

Generators can register themselves when their module is imported:

```python
# At the bottom of your generator file
from boards.generators.registry import registry
registry.register(MyGenerator())
```

### Manual Registration

For more control, register generators manually:

```python
from boards.generators.registry import registry
from my_generators import MyGenerator

def setup_generators():
    registry.register(MyGenerator())
    # Register other generators...

# Call during application startup
setup_generators()
```

## Frontend Integration

Once your generator is registered, the frontend automatically gets:

1. **TypeScript types** generated from your Pydantic schemas
2. **Form UI** with appropriate input fields
3. **Drag/drop zones** for artifact inputs
4. **Validation** based on your schema constraints

The frontend will automatically create:
- Text inputs for `str` fields
- Number inputs for `int`/`float` fields  
- Dropdowns for fields with `enum` constraints
- Drag/drop zones for `*Artifact` fields
- Sliders for fields with `ge`/`le` constraints

## Example Integration

Here's how your generator would be used from the frontend:

```typescript
// TypeScript types auto-generated from Pydantic
interface TTSInput {
  text_source: TextArtifact;
  voice_id: string; 
  stability: number;
  clarity: number;
}

// UI automatically generated
<GeneratorForm 
  generatorName="elevenlabs-tts"
  onSubmit={handleGeneration}
/>
```

This creates a form with:
- A drag/drop zone for `text_source` (accepts text artifacts only)
- A text input for `voice_id`
- Sliders for `stability` and `clarity` (constrained 0.0-1.0)

## Need Help?

- Check existing generators in `boards/generators/implementations/` for examples
- All generators follow the same simple pattern
- The system handles artifact resolution, storage, and UI generation automatically
- Focus on your generation logic - the framework handles the rest!