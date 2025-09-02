# Artifact Types

Artifacts are strongly-typed objects that represent generated content in the Boards system. They enable type-safe chaining between generators and provide metadata about generated content.

## Overview

Every piece of generated content (images, videos, audio, text, LoRA models) is wrapped in an artifact object that contains:

- **Storage information** (where the content is stored)
- **Metadata** (dimensions, duration, format, etc.)
- **Generation tracking** (which generation created it)
- **Type safety** for frontend/backend integration

## Core Artifact Types

### ImageArtifact

Represents generated or input images.

```python
from boards.generators.artifacts import ImageArtifact

image = ImageArtifact(
    generation_id="gen_12345",
    storage_url="https://storage.example.com/images/sunset.png",
    width=1024,
    height=768, 
    format="png"
)

# Access properties
print(f"Image size: {image.width}x{image.height}")
print(f"Aspect ratio: {image.width / image.height:.2f}")
print(f"File format: {image.format}")
```

**Fields:**
- `generation_id` (required): ID of the generation that created this image
- `storage_url` (required): URL where the image file is stored
- `width` (required): Image width in pixels
- `height` (required): Image height in pixels  
- `format` (required): File format (png, jpg, webp, gif, etc.)

**Common Formats:**
- `"png"` - PNG format, supports transparency
- `"jpg"` / `"jpeg"` - JPEG format, smaller file size
- `"webp"` - Modern format, good compression
- `"gif"` - Animated images

### VideoArtifact

Represents generated or input videos.

```python
from boards.generators.artifacts import VideoArtifact

video = VideoArtifact(
    generation_id="gen_67890",
    storage_url="https://storage.example.com/videos/animation.mp4",
    width=1920,
    height=1080,
    format="mp4",
    duration=30.5,    # Optional: duration in seconds
    fps=30.0          # Optional: frames per second
)

# Calculate additional properties
total_frames = video.duration * video.fps if video.duration and video.fps else None
print(f"Video: {video.width}x{video.height} @ {video.fps}fps for {video.duration}s")
```

**Required Fields:**
- `generation_id`: Generation that created this video
- `storage_url`: URL where video is stored
- `width`: Video width in pixels
- `height`: Video height in pixels
- `format`: Video format

**Optional Fields:**
- `duration`: Duration in seconds (float)
- `fps`: Frames per second (float)

**Common Formats:**
- `"mp4"` - Most common, widely supported
- `"webm"` - Web-optimized format
- `"mov"` - QuickTime format
- `"avi"` - Legacy format

### AudioArtifact

Represents generated or input audio files.

```python
from boards.generators.artifacts import AudioArtifact

audio = AudioArtifact(
    generation_id="gen_54321",
    storage_url="https://storage.example.com/audio/speech.mp3",
    format="mp3",
    duration=120.0,      # Optional: 2 minutes
    sample_rate=44100,   # Optional: CD quality
    channels=2           # Optional: stereo
)

# Audio properties
print(f"Audio: {audio.duration}s, {audio.sample_rate}Hz, {audio.channels} channels")
bitrate_estimate = audio.sample_rate * 16 * audio.channels if audio.sample_rate and audio.channels else None
```

**Required Fields:**
- `generation_id`: Generation that created this audio
- `storage_url`: URL where audio is stored  
- `format`: Audio format

**Optional Fields:**
- `duration`: Duration in seconds (float)
- `sample_rate`: Sample rate in Hz (int)
- `channels`: Number of audio channels (int)

**Common Formats:**
- `"mp3"` - Compressed, widely supported
- `"wav"` - Uncompressed, high quality
- `"flac"` - Lossless compression
- `"ogg"` - Open source format
- `"m4a"` - Apple's format

### TextArtifact

Represents generated or input text content.

```python
from boards.generators.artifacts import TextArtifact

text = TextArtifact(
    generation_id="gen_98765",
    content="This is the generated text content...",
    format="plain"  # Optional, defaults to "plain"
)

# Access content directly
print(f"Text length: {len(text.content)} characters")
word_count = len(text.content.split())
print(f"Word count: {word_count}")
```

**Fields:**
- `generation_id` (required): Generation that created this text
- `content` (required): The actual text content
- `format` (optional): Text format, defaults to "plain"

**Text Formats:**
- `"plain"` - Plain text (default)
- `"markdown"` - Markdown formatted text  
- `"html"` - HTML content
- `"json"` - JSON data
- `"code"` - Source code
- `"csv"` - CSV data

**Special Note:** Unlike other artifacts, TextArtifact stores content directly, not via a URL. Use `text.content` to access the text, not `resolve_artifact()`.

### LoRArtifact  

Represents LoRA (Low-Rank Adaptation) model files.

```python
from boards.generators.artifacts import LoRArtifact

lora = LoRArtifact(
    generation_id="gen_13579",
    storage_url="https://storage.example.com/loras/anime_style.safetensors",
    base_model="stable-diffusion-v1-5",
    format="safetensors",
    trigger_words=["anime_style", "illustration", "cel_shading"]  # Optional
)

# LoRA information
print(f"LoRA for {lora.base_model}")
if lora.trigger_words:
    print(f"Trigger words: {', '.join(lora.trigger_words)}")
```

**Fields:**
- `generation_id` (required): Generation that created this LoRA
- `storage_url` (required): URL where LoRA file is stored
- `base_model` (required): Base model this LoRA was trained on
- `format` (required): File format
- `trigger_words` (optional): List of trigger words for this LoRA

**Common Base Models:**
- `"stable-diffusion-v1-5"`
- `"stable-diffusion-xl-base-1.0"`
- `"flux-1-dev"`

**Common Formats:**
- `"safetensors"` - Secure format (recommended)
- `"ckpt"` - Legacy checkpoint format
- `"bin"` - Binary format

## Using Artifacts in Generators

### As Input Parameters

Artifacts can be used as input parameters to create generator chains:

```python
from pydantic import BaseModel, Field
from boards.generators.artifacts import ImageArtifact, AudioArtifact

class LipsyncInput(BaseModel):
    """Input for lip sync generator."""
    video_source: VideoArtifact = Field(description="Video to sync lips in")
    audio_source: AudioArtifact = Field(description="Audio to sync to")
    strength: float = Field(default=0.8, ge=0.0, le=1.0, description="Sync strength")

class StyleTransferInput(BaseModel):
    """Input for style transfer generator."""
    content_image: ImageArtifact = Field(description="Image to apply style to")
    style_image: ImageArtifact = Field(description="Style reference image")
    style_strength: float = Field(default=0.75, ge=0.0, le=1.0)
```

### Resolving Artifacts

Use `resolve_artifact()` to get file paths for provider SDKs:

```python
from boards.generators.resolution import resolve_artifact

class MyGenerator(BaseGenerator):
    async def generate(self, inputs: MyInput) -> MyOutput:
        # Resolve artifacts to file paths
        if inputs.reference_image:
            image_path = await resolve_artifact(inputs.reference_image)
            print(f"Using image at: {image_path}")
        
        if inputs.background_audio:
            audio_path = await resolve_artifact(inputs.background_audio)
        
        # TextArtifact is special - use .content directly
        if inputs.text_prompt:
            text_content = inputs.text_prompt.content
        
        # Pass file paths to provider SDK
        result = await provider_sdk.process(
            image=image_path,
            audio=audio_path,
            text=text_content
        )
        
        return result
```

### Creating Output Artifacts

Use the storage helper functions to create artifacts:

```python
from boards.generators.resolution import (
    store_image_result,
    store_video_result, 
    store_audio_result
)

class MyGenerator(BaseGenerator):
    async def generate(self, inputs: MyInput) -> MyOutput:
        # ... generation logic ...
        
        # Create image artifact
        image_artifact = await store_image_result(
            storage_url=result_image_url,
            format="png",
            generation_id="gen_123",
            width=1024,
            height=1024
        )
        
        # Create text artifact directly
        text_artifact = TextArtifact(
            generation_id="gen_123", 
            content="Generated text content",
            format="plain"
        )
        
        return MyOutput(
            image=image_artifact,
            description=text_artifact
        )
```

## Advanced Patterns

### Multiple Artifacts

Generators can work with lists of artifacts:

```python
class CollageInput(BaseModel):
    source_images: list[ImageArtifact] = Field(
        description="Images to combine into collage",
        min_items=2,
        max_items=9
    )
    layout: str = Field(default="grid", description="Collage layout")

async def generate(self, inputs: CollageInput) -> CollageOutput:
    # Resolve all images
    image_paths = []
    for img_artifact in inputs.source_images:
        path = await resolve_artifact(img_artifact)
        image_paths.append(path)
    
    # Create collage
    result = await collage_sdk.create_collage(
        images=image_paths,
        layout=inputs.layout
    )
    
    return CollageOutput(collage=result_artifact)
```

### Conditional Artifacts

Some inputs might be optional or conditional:

```python
from typing import Optional

class ConditionalInput(BaseModel):
    mode: str = Field(pattern="^(generate|modify)$")
    prompt: str = Field(description="Generation prompt")
    
    # Only required for modify mode
    base_image: Optional[ImageArtifact] = Field(
        None, 
        description="Base image to modify (required for modify mode)"
    )
    
    @model_validator(mode='after')
    def validate_conditional_fields(self) -> Self:
        if self.mode == "modify" and not self.base_image:
            raise ValueError("base_image is required when mode='modify'")
        return self

async def generate(self, inputs: ConditionalInput):
    if inputs.mode == "generate":
        # Text-to-image generation
        result = await text_to_image(inputs.prompt)
    else:  # modify mode
        # Image-to-image with base
        base_path = await resolve_artifact(inputs.base_image)
        result = await image_to_image(inputs.prompt, base_path)
    
    return result
```

### Artifact Metadata Extraction

You can extract useful information from artifacts:

```python
def analyze_artifact(artifact):
    """Extract useful information from an artifact."""
    
    if isinstance(artifact, ImageArtifact):
        aspect_ratio = artifact.width / artifact.height
        megapixels = (artifact.width * artifact.height) / 1_000_000
        
        return {
            "type": "image",
            "dimensions": f"{artifact.width}x{artifact.height}",
            "aspect_ratio": f"{aspect_ratio:.2f}",
            "megapixels": f"{megapixels:.1f}MP",
            "format": artifact.format
        }
    
    elif isinstance(artifact, VideoArtifact):
        total_pixels = artifact.width * artifact.height
        if artifact.duration and artifact.fps:
            total_frames = artifact.duration * artifact.fps
        else:
            total_frames = None
            
        return {
            "type": "video",
            "resolution": f"{artifact.width}x{artifact.height}",
            "duration": f"{artifact.duration}s" if artifact.duration else "unknown",
            "fps": artifact.fps,
            "total_frames": total_frames,
            "format": artifact.format
        }
    
    elif isinstance(artifact, AudioArtifact):
        if artifact.sample_rate and artifact.channels:
            quality_desc = f"{artifact.sample_rate}Hz, {artifact.channels}ch"
        else:
            quality_desc = "unknown quality"
            
        return {
            "type": "audio",
            "duration": f"{artifact.duration}s" if artifact.duration else "unknown", 
            "quality": quality_desc,
            "format": artifact.format
        }
```

## Frontend Integration

### TypeScript Type Generation

Your Pydantic artifacts automatically generate TypeScript interfaces:

```python
# Python
class MyInput(BaseModel):
    reference_image: ImageArtifact
    prompt: str
    strength: float = Field(ge=0.0, le=1.0)
```

```typescript
// Auto-generated TypeScript
interface MyInput {
  reference_image: ImageArtifact;
  prompt: string;
  strength: number; // Will be a slider from 0.0 to 1.0
}

interface ImageArtifact {
  generation_id: string;
  storage_url: string;
  width: number;
  height: number; 
  format: string;
}
```

### UI Generation

The frontend automatically creates appropriate controls:

- **Artifact fields** → Drag/drop zones with type validation
- **Text fields** → Text inputs
- **Numeric fields with bounds** → Sliders
- **Enum fields** → Dropdowns
- **Boolean fields** → Checkboxes
- **Array fields** → Multi-select or repeatable inputs

### Drag and Drop Validation

The frontend validates that only compatible artifacts can be dropped:

```typescript
// Only ImageArtifacts can be dropped in image slots
<ArtifactDropZone 
  acceptTypes={["image"]}
  onDrop={(artifact: ImageArtifact) => setReferenceImage(artifact)}
/>

// AudioArtifacts for audio slots
<ArtifactDropZone
  acceptTypes={["audio"]} 
  onDrop={(artifact: AudioArtifact) => setBackgroundMusic(artifact)}
/>

// Multiple types accepted
<ArtifactDropZone
  acceptTypes={["image", "video"]}
  onDrop={(artifact: ImageArtifact | VideoArtifact) => setSource(artifact)}
/>
```

## Best Practices

### 1. **Use Appropriate Types**
Choose the right artifact type for your content:
- Images → `ImageArtifact`
- Videos → `VideoArtifact`  
- Audio → `AudioArtifact`
- Text content → `TextArtifact`
- ML models → `LoRArtifact`

### 2. **Provide Rich Metadata**
Include as much metadata as possible:
```python
# Good - includes optional metadata
VideoArtifact(
    generation_id="gen_123",
    storage_url="video.mp4",
    width=1920,
    height=1080,
    format="mp4",
    duration=30.0,
    fps=24.0
)

# Less useful - minimal metadata
VideoArtifact(
    generation_id="gen_123", 
    storage_url="video.mp4",
    width=1920,
    height=1080,
    format="mp4"
)
```

### 3. **Validate Artifact Compatibility**
Check that input artifacts are suitable for your generator:

```python
@field_validator('input_video')
@classmethod
def validate_video_duration(cls, v: VideoArtifact) -> VideoArtifact:
    if v.duration and v.duration > 300:  # 5 minutes
        raise ValueError("Video must be shorter than 5 minutes")
    return v

@field_validator('reference_image')
@classmethod
def validate_image_size(cls, v: ImageArtifact) -> ImageArtifact:
    if v.width < 512 or v.height < 512:
        raise ValueError("Image must be at least 512x512 pixels")
    return v
```

### 4. **Handle Missing Metadata Gracefully**
Not all artifacts will have complete metadata:

```python
def get_video_info(video: VideoArtifact) -> str:
    info = f"{video.width}x{video.height}"
    
    if video.fps:
        info += f" @ {video.fps}fps"
    
    if video.duration:
        info += f" for {video.duration:.1f}s"
    
    return info
```

### 5. **Use Meaningful Descriptions**
Field descriptions become UI help text:

```python
class WellDocumentedInput(BaseModel):
    source_image: ImageArtifact = Field(
        description="Reference image for style transfer. Works best with high-contrast images."
    )
    style_strength: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="How strongly to apply the style (0.0 = original image, 1.0 = full style)"
    )
```

This comprehensive artifact system enables type-safe, chainable generators with rich metadata and automatic UI generation!