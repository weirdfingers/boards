# Generator Input Schemas

Generator input schemas define the parameters that a generator accepts. They are built using Pydantic models and automatically converted to JSON Schema for dynamic UI generation.

## Overview

Every generator must implement `get_input_schema()` which returns a Pydantic `BaseModel` class. This model defines:

- **Artifact inputs**: References to existing artifacts (audio, video, image, text)
- **Prompt field**: Text input for generation instructions
- **Settings**: Additional parameters like sliders, dropdowns, and text inputs

The backend automatically serializes these Pydantic models to JSON Schema using `.model_json_schema()`, which is then sent to the frontend for dynamic UI generation.

## Basic Example

```python
from pydantic import BaseModel, Field
from boards.artifacts import ImageArtifact
from boards.generators.base import BaseGenerator

class MyGeneratorInput(BaseModel):
    """Input schema for my custom generator."""

    prompt: str = Field(description="Text prompt for generation")
    style: str = Field(default="realistic", description="Art style")

class MyGenerator(BaseGenerator):
    name = "my-generator"
    artifact_type = "image"
    description = "Custom image generator"

    def get_input_schema(self) -> type[MyGeneratorInput]:
        return MyGeneratorInput

    async def generate(self, inputs: MyGeneratorInput, context):
        # Implementation here
        pass
```

## Field Types

### Artifact References

Artifact fields allow users to select existing artifacts from their board as inputs to the generator.

#### Single Artifact

```python
from boards.artifacts import AudioArtifact, VideoArtifact, ImageArtifact

class LipsyncInput(BaseModel):
    audio_source: AudioArtifact = Field(description="Audio track for lip sync")
    video_source: VideoArtifact = Field(description="Video to sync lips in")
```

**Generated JSON Schema:**
```json
{
  "properties": {
    "audio_source": {
      "$ref": "#/$defs/AudioArtifact",
      "description": "Audio track for lip sync"
    },
    "video_source": {
      "$ref": "#/$defs/VideoArtifact",
      "description": "Video to sync lips in"
    }
  },
  "required": ["audio_source", "video_source"]
}
```

#### Array of Artifacts

For generators that accept multiple artifacts of the same type:

```python
class MultiImageInput(BaseModel):
    reference_images: list[ImageArtifact] = Field(
        description="Reference images for style transfer"
    )
```

**Generated JSON Schema:**
```json
{
  "properties": {
    "reference_images": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/ImageArtifact"
      },
      "description": "Reference images for style transfer",
      "title": "Reference Images"
    }
  },
  "required": ["reference_images"]
}
```

You can also constrain array length:

```python
from pydantic import Field

class ConstrainedArrayInput(BaseModel):
    images: list[ImageArtifact] = Field(
        min_length=1,
        max_length=5,
        description="1-5 reference images"
    )
```

### Prompt Field

The `prompt` field is a special string field that appears as a prominent textarea in the UI:

```python
class GeneratorInput(BaseModel):
    prompt: str = Field(description="Text prompt for image generation")
```

The field **must be named exactly "prompt"** to receive special UI treatment.

For optional prompts:

```python
class OptionalPromptInput(BaseModel):
    prompt: str | None = Field(None, description="Optional generation prompt")
```

### Settings Fields

Settings fields appear in a separate settings panel in the UI.

#### Sliders (Numeric Ranges)

Use `ge` (greater than or equal) and `le` (less than or equal) to create slider inputs:

```python
class SliderInput(BaseModel):
    strength: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Strength of the effect"
    )

    steps: int = Field(
        default=50,
        ge=1,
        le=150,
        description="Number of inference steps"
    )
```

**Generated JSON Schema:**
```json
{
  "properties": {
    "strength": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "default": 0.7,
      "description": "Strength of the effect"
    },
    "steps": {
      "type": "integer",
      "minimum": 1,
      "maximum": 150,
      "default": 50,
      "description": "Number of inference steps"
    }
  }
}
```

#### Dropdowns (Enums)

Use `Literal` types to create dropdown selectors:

```python
from typing import Literal

class DropdownInput(BaseModel):
    style: Literal['realistic', 'anime', 'abstract', 'oil-painting'] = Field(
        default='realistic',
        description="Art style"
    )

    aspect_ratio: Literal['1:1', '16:9', '4:3', '9:16'] = Field(
        default='1:1',
        description="Image aspect ratio"
    )
```

**Generated JSON Schema:**
```json
{
  "properties": {
    "style": {
      "type": "string",
      "enum": ["realistic", "anime", "abstract", "oil-painting"],
      "default": "realistic",
      "description": "Art style"
    }
  }
}
```

#### Text Inputs

Simple string fields become text input boxes:

```python
class TextInput(BaseModel):
    negative_prompt: str = Field(
        default="",
        description="Things to avoid in generation"
    )
```

You can add pattern validation:

```python
class PatternInput(BaseModel):
    hex_color: str = Field(
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Hex color code"
    )
```

#### Number Inputs

Numeric fields without `ge`/`le` constraints become number input boxes:

```python
class NumberInput(BaseModel):
    seed: int = Field(
        default=-1,
        description="Random seed (-1 for random)"
    )

    temperature: float = Field(
        default=1.0,
        description="Sampling temperature"
    )
```

## Complete Example

Here's a comprehensive example combining all field types:

```python
from pydantic import BaseModel, Field
from typing import Literal
from boards.artifacts import ImageArtifact, AudioArtifact

class AdvancedGeneratorInput(BaseModel):
    """Input schema demonstrating all field types."""

    # Artifact inputs
    base_image: ImageArtifact = Field(
        description="Base image to transform"
    )
    reference_images: list[ImageArtifact] = Field(
        default=[],
        max_length=3,
        description="Up to 3 reference images"
    )
    audio_track: AudioArtifact | None = Field(
        None,
        description="Optional audio for synchronization"
    )

    # Prompt
    prompt: str = Field(
        description="Describe the desired output"
    )

    # Settings - Sliders
    strength: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Effect strength"
    )
    steps: int = Field(
        default=50,
        ge=20,
        le=100,
        description="Number of inference steps"
    )

    # Settings - Dropdown
    style: Literal['realistic', 'artistic', 'anime'] = Field(
        default='realistic',
        description="Output style"
    )

    # Settings - Text input
    negative_prompt: str = Field(
        default="",
        description="What to avoid"
    )

    # Settings - Number input
    seed: int = Field(
        default=-1,
        description="Random seed"
    )
```

## Best Practices

### Field Naming

- Use `snake_case` for field names
- Use descriptive names that indicate the field's purpose
- For artifact fields, include the artifact type in the name: `audio_source`, `video_input`, `reference_images`

### Descriptions

Always provide clear `description` parameters - these appear as help text in the UI:

```python
prompt: str = Field(description="Describe what you want to generate")
```

### Titles

Pydantic automatically generates titles from field names, but you can customize them:

```python
reference_imgs: list[ImageArtifact] = Field(
    title="Reference Images",
    description="Style reference images"
)
```

### Defaults

Provide sensible defaults for optional fields:

```python
steps: int = Field(default=50, ge=1, le=150)
style: Literal['realistic', 'anime'] = Field(default='realistic')
```

### Required vs Optional

Fields without defaults are required. Use `| None` with `default=None` for optional fields:

```python
# Required
prompt: str = Field(description="Required prompt")

# Optional
negative_prompt: str | None = Field(None, description="Optional negative prompt")
```

### Validation

Use Pydantic's built-in validators for complex validation:

```python
from pydantic import field_validator

class ValidatedInput(BaseModel):
    seed: int = Field(description="Random seed")

    @field_validator('seed')
    @classmethod
    def validate_seed(cls, v: int) -> int:
        if v < -1:
            raise ValueError("Seed must be >= -1")
        return v
```

## JSON Schema Output

The Pydantic model is automatically converted to JSON Schema:

```python
schema = MyGeneratorInput.model_json_schema()
```

This JSON Schema is sent to the frontend via GraphQL and used to dynamically generate the UI. The frontend's `parseGeneratorSchema` utility parses this JSON Schema into structured data for rendering.

## See Also

- [Creating Generators](./creating-generators.md) - Full generator implementation guide
- [Frontend Generator UI](../frontend/generator-ui.md) - Building custom UIs from schemas
- [Pydantic Documentation](https://docs.pydantic.dev/) - Complete Pydantic reference
