# Artifact Resolution Guide

This guide explains how artifact resolution works in the Boards generator system.

## Overview

Generators can accept artifacts (images, videos, audio, etc.) from previous generations as inputs. The artifact resolution system automatically converts generation ID strings (UUIDs) into typed artifact objects with proper validation.

## How It Works

### Automatic Type Introspection

The system uses Pydantic type introspection to automatically detect which fields are artifacts. **No manual configuration needed!**

```python
from pydantic import BaseModel, Field
from boards.generators.artifacts import ImageArtifact, VideoArtifact

class MyGeneratorInput(BaseModel):
    """Input schema for my generator."""

    prompt: str = Field(description="Text prompt")

    # These are automatically detected as artifact fields
    image_source: ImageArtifact = Field(description="Input image")
    video_sources: list[VideoArtifact] = Field(description="Input videos")

    # Regular fields are ignored
    num_outputs: int = Field(default=1, ge=1, le=10)
```

That's it! No decorators, no class variables, no manual registration needed.

### What Happens Automatically

When a generation is submitted with input parameters like:

```json
{
  "prompt": "enhance the colors",
  "image_source": "550e8400-e29b-41d4-a716-446655440000",
  "video_sources": [
    "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "8f9e6679-7425-40de-944b-e07fc1f90ae8"
  ]
}
```

The system:

1. **Detects** that `image_source` and `video_sources` are artifact fields (via type introspection)
2. **Queries** the database to fetch the generations by ID
3. **Validates** each generation:
   - Belongs to the same tenant (access control)
   - Has status="completed" (can't use pending generations)
   - Has the correct artifact type (can't use a video where an image is expected)
4. **Converts** generation records to typed artifact objects
5. **Validates** the input with Pydantic

All of this happens automatically in [actors.py](src/boards/workers/actors.py:92-112).

## Supported Patterns

### Single Artifact

```python
image_source: ImageArtifact = Field(...)
```

**Input**: Single generation ID string (e.g., `"550e8400-e29b-41d4-a716-446655440000"`)
**Output**: Single `ImageArtifact` object

### List of Artifacts

```python
image_sources: list[ImageArtifact] = Field(min_length=1)
```

**Input**: List of generation ID strings (e.g., `["id1", "id2"]`)
**Output**: List of `ImageArtifact` objects (always a list, even if input has one ID)

**Important**: If the field type is `list[ImageArtifact]`, the resolved value will ALWAYS be a list, even if only one generation ID is provided. The system respects the type annotation.

### Optional Artifacts

```python
reference_image: ImageArtifact | None = Field(default=None)
```

Field can be omitted or set to `null`.

## Supported Artifact Types

- `ImageArtifact` - Images (PNG, JPEG, WebP, etc.)
- `VideoArtifact` - Videos (MP4, WebM, etc.)
- `AudioArtifact` - Audio files (MP3, WAV, etc.)
- `TextArtifact` - Text content

## Error Handling

The system provides clear error messages when validation fails:

- `"Generation {id} not found"` - Invalid generation ID
- `"Access denied to generation {id} - tenant mismatch"` - User doesn't own this generation
- `"Generation {id} is not completed (status: pending)"` - Can't use incomplete generations
- `"Generation {id} has wrong artifact type: expected image, got video"` - Type mismatch

## Examples

### Image-to-Image Editor

```python
class ImageEditInput(BaseModel):
    prompt: str = Field(description="Editing instructions")
    image_source: ImageArtifact = Field(description="Image to edit")
    strength: float = Field(default=0.8, ge=0.0, le=1.0)
```

### Multi-Image Collage

```python
class CollageInput(BaseModel):
    images: list[ImageArtifact] = Field(
        description="Images to combine",
        min_length=2,
        max_length=9
    )
    layout: Literal["grid", "freeform"] = Field(default="grid")
```

### Video + Audio Mixer

```python
class VideoAudioMixInput(BaseModel):
    video_source: VideoArtifact = Field(description="Video track")
    audio_source: AudioArtifact = Field(description="Audio track")
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
```

## Implementation Details

The automatic detection is handled by:

- [`extract_artifact_fields()`](src/boards/generators/artifact_resolution.py:62-90) - Introspects schema to find artifact fields
- [`resolve_input_artifacts()`](src/boards/generators/artifact_resolution.py:252-344) - Resolves generation IDs to artifacts
- [`resolve_generation_ids_to_artifacts()`](src/boards/generators/artifact_resolution.py:150-249) - Database queries and validation

See [artifact_resolution.py](src/boards/generators/artifact_resolution.py) for the full implementation.
