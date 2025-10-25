# Generator Examples

This guide showcases real-world generator implementations that demonstrate different patterns and integration approaches.

## Text-to-Image Generators

### FLUX Pro Generator

A high-quality text-to-image generator using Replicate's FLUX.1.1 Pro model:

```python
from typing import Type
from pydantic import BaseModel, Field
from boards.generators.base import BaseGenerator
from boards.generators.artifacts import ImageArtifact
from boards.generators.resolution import store_image_result
from boards.generators.registry import registry

class FluxProInput(BaseModel):
    prompt: str = Field(description="Text prompt for image generation")
    aspect_ratio: str = Field(
        default="1:1",
        description="Image aspect ratio",
        pattern="^(1:1|16:9|21:9|2:3|3:2|4:5|5:4|9:16|9:21)$"
    )
    safety_tolerance: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Safety tolerance level (1-5)"
    )

class FluxProOutput(BaseModel):
    image: ImageArtifact

class FluxProGenerator(BaseGenerator):
    name = "flux-pro"
    artifact_type = "image"
    description = "FLUX.1.1 [pro] by Black Forest Labs - high-quality image generation"
    
    def get_input_schema(self) -> Type[FluxProInput]:
        return FluxProInput
    
    async def generate(self, inputs: FluxProInput) -> FluxProOutput:
        import os
        import replicate
        
        if not os.getenv("REPLICATE_API_TOKEN"):
            raise ValueError("REPLICATE_API_TOKEN environment variable is required")
        
        prediction = await replicate.async_run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": inputs.prompt,
                "aspect_ratio": inputs.aspect_ratio,
                "safety_tolerance": inputs.safety_tolerance,
            }
        )
        
        output_url = prediction[0] if isinstance(prediction, list) else prediction
        
        image_artifact = await store_image_result(
            storage_url=output_url,
            format="png",
            generation_id="temp_gen_id",
            width=1024,
            height=1024
        )
        
        return FluxProOutput(image=image_artifact)
    
    async def estimate_cost(self, inputs: FluxProInput) -> float:
        return 0.055  # FLUX.1.1 Pro pricing

registry.register(FluxProGenerator())
```

### Style Transfer Generator

An image-to-image generator that applies artistic styles:

```python
from typing import Optional
from pydantic import BaseModel, Field

class StyleTransferInput(BaseModel):
    content_image: ImageArtifact = Field(description="Image to apply style to")
    style_reference: Optional[ImageArtifact] = Field(
        None, 
        description="Style reference image (optional)"
    )
    style_prompt: Optional[str] = Field(
        None,
        description="Text description of desired style"
    )
    style_strength: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="How strongly to apply the style"
    )
    
    @model_validator(mode='after')
    def validate_style_inputs(self) -> Self:
        if not self.style_reference and not self.style_prompt:
            raise ValueError("Either style_reference or style_prompt must be provided")
        return self

class StyleTransferGenerator(BaseGenerator):
    name = "style-transfer"
    artifact_type = "image"
    description = "Apply artistic styles to images"
    
    async def generate(self, inputs: StyleTransferInput) -> ImageOutput:
        from boards.generators.resolution import resolve_artifact
        
        # Resolve content image to file path
        content_path = await resolve_artifact(inputs.content_image)
        
        # Handle style reference if provided
        style_path = None
        if inputs.style_reference:
            style_path = await resolve_artifact(inputs.style_reference)
        
        # Use provider SDK
        import replicate
        
        api_inputs = {
            "image": open(content_path, "rb"),
            "strength": inputs.style_strength
        }
        
        if style_path:
            api_inputs["style_image"] = open(style_path, "rb")
        if inputs.style_prompt:
            api_inputs["style_prompt"] = inputs.style_prompt
        
        result = await replicate.async_run("style-transfer-model", input=api_inputs)
        
        output_artifact = await store_image_result(
            storage_url=result,
            format="png",
            generation_id="temp_gen_id",
            width=inputs.content_image.width,
            height=inputs.content_image.height
        )
        
        return ImageOutput(image=output_artifact)
```

## Video Generators

### Lip Sync Generator

A video generator that syncs lips to audio:

```python
from boards.generators.artifacts import VideoArtifact, AudioArtifact

class LipsyncInput(BaseModel):
    video_source: VideoArtifact = Field(description="Video to sync lips in")
    audio_source: AudioArtifact = Field(description="Audio track for lip sync")
    quality: str = Field(
        default="medium",
        description="Output quality",
        pattern="^(low|medium|high)$"
    )

class LipsyncOutput(BaseModel):
    video: VideoArtifact

class LipsyncGenerator(BaseGenerator):
    name = "lipsync"
    artifact_type = "video"
    description = "Sync lips in video to match audio track"
    
    async def generate(self, inputs: LipsyncInput) -> LipsyncOutput:
        from boards.generators.resolution import resolve_artifact, store_video_result
        
        # Resolve both input artifacts
        video_path = await resolve_artifact(inputs.video_source)
        audio_path = await resolve_artifact(inputs.audio_source)
        
        import replicate
        
        result = await replicate.async_run(
            "cjwbw/wav2lip",
            input={
                "video": open(video_path, "rb"),
                "audio": open(audio_path, "rb"),
                "quality": inputs.quality
            }
        )
        
        video_artifact = await store_video_result(
            storage_url=result,
            format="mp4",
            generation_id="temp_gen_id",
            width=inputs.video_source.width,
            height=inputs.video_source.height,
            duration=inputs.audio_source.duration,
            fps=inputs.video_source.fps
        )
        
        return LipsyncOutput(video=video_artifact)
    
    async def estimate_cost(self, inputs: LipsyncInput) -> float:
        # Cost based on video duration
        duration = inputs.video_source.duration or 10  # Default 10s
        base_cost = 0.01
        duration_cost = duration * 0.002  # $0.002 per second
        
        quality_multiplier = {"low": 1.0, "medium": 1.5, "high": 2.0}[inputs.quality]
        
        return (base_cost + duration_cost) * quality_multiplier
```

### Video Upscaling Generator

Enhance video resolution and quality:

```python
class VideoUpscaleInput(BaseModel):
    source_video: VideoArtifact = Field(description="Video to upscale")
    target_resolution: str = Field(
        default="1080p",
        description="Target resolution",
        pattern="^(720p|1080p|1440p|4K)$"
    )
    enhance_faces: bool = Field(
        default=True,
        description="Apply face enhancement"
    )
    denoise_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Noise reduction strength"
    )

class VideoUpscaleGenerator(BaseGenerator):
    name = "video-upscale"
    artifact_type = "video"
    description = "Enhance video resolution and quality"
    
    async def generate(self, inputs: VideoUpscaleInput) -> VideoOutput:
        video_path = await resolve_artifact(inputs.source_video)
        
        # Calculate target dimensions
        resolution_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080), 
            "1440p": (2560, 1440),
            "4K": (3840, 2160)
        }
        target_width, target_height = resolution_map[inputs.target_resolution]
        
        import fal_client
        
        result = await fal_client.submit(
            "fal-ai/video-upscaler",
            arguments={
                "video_url": inputs.source_video.storage_url,
                "target_width": target_width,
                "target_height": target_height,
                "enhance_faces": inputs.enhance_faces,
                "denoise_level": inputs.denoise_level
            }
        )
        
        upscaled_video = await store_video_result(
            storage_url=result["video"]["url"],
            format="mp4",
            generation_id="temp_gen_id",
            width=target_width,
            height=target_height,
            duration=inputs.source_video.duration,
            fps=inputs.source_video.fps
        )
        
        return VideoOutput(video=upscaled_video)
    
    async def estimate_cost(self, inputs: VideoUpscaleInput) -> float:
        # Cost based on source resolution and duration
        source_pixels = inputs.source_video.width * inputs.source_video.height
        duration = inputs.source_video.duration or 10
        
        base_cost = 0.05
        pixel_cost = (source_pixels / 1_000_000) * 0.01  # Per megapixel
        duration_cost = duration * 0.005  # Per second
        
        return base_cost + pixel_cost + duration_cost
```

## Audio Generators

### Text-to-Speech Generator

Convert text to speech with voice options:

```python
from boards.generators.artifacts import TextArtifact, AudioArtifact

class TTSInput(BaseModel):
    text_source: TextArtifact = Field(description="Text to convert to speech")
    voice: str = Field(
        default="alloy",
        description="Voice to use for generation"
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Speech speed multiplier"
    )
    output_format: str = Field(
        default="mp3",
        description="Audio format",
        pattern="^(mp3|wav|flac|aac)$"
    )

class TTSOutput(BaseModel):
    audio: AudioArtifact

class TTSGenerator(BaseGenerator):
    name = "text-to-speech"
    artifact_type = "audio" 
    description = "Convert text to speech using AI voices"
    
    async def generate(self, inputs: TTSInput) -> TTSOutput:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI()
        
        response = await client.audio.speech.create(
            model="tts-1",
            voice=inputs.voice,
            input=inputs.text_source.content,
            speed=inputs.speed,
            response_format=inputs.output_format
        )
        
        # Save audio content to temporary file and upload to storage
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=f".{inputs.output_format}") as temp_file:
            temp_file.write(response.content)
            temp_file.flush()
            
            # TODO: Upload to storage and get URL
            storage_url = "https://storage.example.com/generated_audio.mp3"
        
        # Estimate duration from text (rough calculation)
        word_count = len(inputs.text_source.content.split())
        estimated_duration = (word_count / 150) * 60  # ~150 words per minute
        estimated_duration /= inputs.speed  # Adjust for speed
        
        audio_artifact = await store_audio_result(
            storage_url=storage_url,
            format=inputs.output_format,
            generation_id="temp_gen_id",
            duration=estimated_duration,
            sample_rate=22050 if inputs.output_format == "mp3" else 44100,
            channels=1
        )
        
        return TTSOutput(audio=audio_artifact)
    
    async def estimate_cost(self, inputs: TTSInput) -> float:
        # OpenAI TTS pricing: $15/1M characters
        char_count = len(inputs.text_source.content)
        return (char_count / 1_000_000) * 15.0
```

### Music Generation

Generate background music from prompts:

```python
class MusicGenerationInput(BaseModel):
    prompt: str = Field(description="Description of the music to generate")
    duration: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Duration in seconds"
    )
    genre: Optional[str] = Field(
        None,
        description="Music genre (optional)"
    )
    mood: Optional[str] = Field(
        None,
        description="Mood/energy level (optional)"
    )
    instrumental: bool = Field(
        default=True,
        description="Generate instrumental music only"
    )

class MusicGenerationGenerator(BaseGenerator):
    name = "music-generation"
    artifact_type = "audio"
    description = "Generate original music from text prompts"
    
    async def generate(self, inputs: MusicGenerationInput) -> AudioOutput:
        import replicate
        
        # Build prompt with genre and mood
        full_prompt = inputs.prompt
        if inputs.genre:
            full_prompt += f", {inputs.genre} genre"
        if inputs.mood:
            full_prompt += f", {inputs.mood} mood"
        if inputs.instrumental:
            full_prompt += ", instrumental"
        
        result = await replicate.async_run(
            "meta/musicgen",
            input={
                "prompt": full_prompt,
                "duration": inputs.duration,
                "top_k": 250,
                "top_p": 0.0,
                "temperature": 1.0
            }
        )
        
        audio_artifact = await store_audio_result(
            storage_url=result,
            format="wav",
            generation_id="temp_gen_id",
            duration=float(inputs.duration),
            sample_rate=32000,
            channels=1
        )
        
        return AudioOutput(audio=audio_artifact)
    
    async def estimate_cost(self, inputs: MusicGenerationInput) -> float:
        # Cost based on duration
        return inputs.duration * 0.002  # $0.002 per second
```

## Multi-Modal Generators

### Image-to-Video Generator

Convert static images to videos:

```python
class ImageToVideoInput(BaseModel):
    source_image: ImageArtifact = Field(description="Image to animate")
    motion_prompt: str = Field(description="Description of desired motion")
    duration: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Video duration in seconds"
    )
    fps: int = Field(
        default=24,
        ge=12,
        le=60,
        description="Frames per second"
    )
    motion_strength: float = Field(
        default=0.7,
        ge=0.1,
        le=1.0,
        description="Strength of motion effect"
    )

class ImageToVideoGenerator(BaseGenerator):
    name = "image-to-video"
    artifact_type = "video"
    description = "Animate static images into videos"
    
    async def generate(self, inputs: ImageToVideoInput) -> VideoOutput:
        image_path = await resolve_artifact(inputs.source_image)
        
        import fal_client
        
        result = await fal_client.submit(
            "fal-ai/stable-video-diffusion",
            arguments={
                "image_url": inputs.source_image.storage_url,
                "motion_prompt": inputs.motion_prompt,
                "duration": inputs.duration,
                "fps": inputs.fps,
                "motion_strength": inputs.motion_strength
            }
        )
        
        video_artifact = await store_video_result(
            storage_url=result["video"]["url"],
            format="mp4",
            generation_id="temp_gen_id", 
            width=inputs.source_image.width,
            height=inputs.source_image.height,
            duration=inputs.duration,
            fps=float(inputs.fps)
        )
        
        return VideoOutput(video=video_artifact)
```

### Audio-to-Video Generator  

Generate visualizations for audio:

```python
class AudioVisualizationInput(BaseModel):
    audio_source: AudioArtifact = Field(description="Audio to visualize")
    visualization_style: str = Field(
        default="waveform",
        description="Visualization style",
        pattern="^(waveform|spectrum|particles|abstract)$"
    )
    color_scheme: str = Field(
        default="blue",
        description="Color scheme for visualization"
    )
    resolution: str = Field(
        default="1080p",
        pattern="^(720p|1080p|1440p)$"
    )
    background_type: str = Field(
        default="dark",
        pattern="^(dark|light|gradient|image)$"
    )

class AudioVisualizationGenerator(BaseGenerator):
    name = "audio-visualization"
    artifact_type = "video"
    description = "Generate video visualizations for audio tracks"
    
    async def generate(self, inputs: AudioVisualizationInput) -> VideoOutput:
        audio_path = await resolve_artifact(inputs.audio_source)
        
        # Resolution mapping
        resolution_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "1440p": (2560, 1440)
        }
        width, height = resolution_map[inputs.resolution]
        
        # Use specialized audio visualization service
        import requests
        
        response = await requests.post(
            "https://audio-viz-api.com/generate",
            json={
                "audio_url": inputs.audio_source.storage_url,
                "style": inputs.visualization_style,
                "colors": inputs.color_scheme,
                "resolution": inputs.resolution,
                "background": inputs.background_type
            }
        )
        
        result_url = response.json()["video_url"]
        
        video_artifact = await store_video_result(
            storage_url=result_url,
            format="mp4",
            generation_id="temp_gen_id",
            width=width,
            height=height,
            duration=inputs.audio_source.duration,
            fps=30.0
        )
        
        return VideoOutput(video=video_artifact)
```

## Advanced Generators

### Batch Image Generator

Process multiple prompts efficiently:

```python
class BatchImageInput(BaseModel):
    prompts: list[str] = Field(
        description="Multiple prompts to generate images for",
        min_items=1,
        max_items=20
    )
    shared_settings: dict = Field(
        default_factory=dict,
        description="Settings to apply to all generations"
    )
    parallel_limit: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum parallel generations"
    )

class BatchImageOutput(BaseModel):
    images: list[ImageArtifact]
    failed_prompts: list[int] = Field(default_factory=list)
    total_cost: float

class BatchImageGenerator(BaseGenerator):
    name = "batch-image"
    artifact_type = "image"
    description = "Generate multiple images from prompts in parallel"
    
    async def generate(self, inputs: BatchImageInput) -> BatchImageOutput:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        results = []
        failed_indices = []
        total_cost = 0.0
        
        semaphore = asyncio.Semaphore(inputs.parallel_limit)
        
        async def generate_single(index: int, prompt: str) -> Optional[ImageArtifact]:
            async with semaphore:
                try:
                    single_input = ImageInput(
                        prompt=prompt,
                        **inputs.shared_settings
                    )
                    
                    # Use the base image generator
                    result = await base_image_generator.generate(single_input)
                    cost = await base_image_generator.estimate_cost(single_input)
                    
                    nonlocal total_cost
                    total_cost += cost
                    
                    return result.image
                    
                except Exception as e:
                    logging.warning(f"Failed to generate image for prompt {index}: {e}")
                    failed_indices.append(index)
                    return None
        
        # Generate all images in parallel
        tasks = [
            generate_single(i, prompt)
            for i, prompt in enumerate(inputs.prompts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_images = [
            img for img in results 
            if isinstance(img, ImageArtifact)
        ]
        
        return BatchImageOutput(
            images=successful_images,
            failed_prompts=failed_indices,
            total_cost=total_cost
        )
    
    async def estimate_cost(self, inputs: BatchImageInput) -> float:
        # Estimate cost for all prompts
        single_input = ImageInput(
            prompt="sample prompt",
            **inputs.shared_settings
        )
        single_cost = await base_image_generator.estimate_cost(single_input)
        return single_cost * len(inputs.prompts)
```

### Conditional Generation Pipeline

Complex generator with multiple modes:

```python
class ConditionalPipelineInput(BaseModel):
    mode: str = Field(
        description="Generation mode", 
        pattern="^(text_to_image|image_to_image|image_to_video|style_transfer)$"
    )
    
    # Text inputs
    prompt: Optional[str] = Field(None)
    negative_prompt: Optional[str] = Field(None)
    
    # Image inputs
    source_image: Optional[ImageArtifact] = Field(None)
    style_image: Optional[ImageArtifact] = Field(None)
    
    # Generation settings
    quality: float = Field(default=0.75, ge=0.0, le=1.0)
    creativity: float = Field(default=0.5, ge=0.0, le=1.0)
    
    @model_validator(mode='after')
    def validate_mode_requirements(self) -> Self:
        if self.mode == "text_to_image" and not self.prompt:
            raise ValueError("prompt required for text_to_image mode")
        elif self.mode == "image_to_image" and (not self.source_image or not self.prompt):
            raise ValueError("source_image and prompt required for image_to_image mode")
        elif self.mode == "style_transfer" and (not self.source_image or not self.style_image):
            raise ValueError("source_image and style_image required for style_transfer mode")
        
        return self

class ConditionalPipelineGenerator(BaseGenerator):
    name = "conditional-pipeline"
    artifact_type = "mixed"  # Can output different types
    description = "Multi-mode generation pipeline with conditional logic"
    
    async def generate(self, inputs: ConditionalPipelineInput) -> BaseModel:
        if inputs.mode == "text_to_image":
            return await self._text_to_image(inputs)
        elif inputs.mode == "image_to_image":
            return await self._image_to_image(inputs)
        elif inputs.mode == "image_to_video":
            return await self._image_to_video(inputs)
        elif inputs.mode == "style_transfer":
            return await self._style_transfer(inputs)
        else:
            raise ValueError(f"Unknown mode: {inputs.mode}")
    
    async def _text_to_image(self, inputs: ConditionalPipelineInput) -> ImageOutput:
        # Implement text-to-image logic
        pass
    
    async def _image_to_image(self, inputs: ConditionalPipelineInput) -> ImageOutput:
        # Implement image-to-image logic
        pass
    
    async def _image_to_video(self, inputs: ConditionalPipelineInput) -> VideoOutput:
        # Implement image-to-video logic  
        pass
    
    async def _style_transfer(self, inputs: ConditionalPipelineInput) -> ImageOutput:
        # Implement style transfer logic
        pass
```

## Generator Registration Patterns

### Automatic Registration

```python
# generators/__init__.py
def register_all_generators():
    """Register all generators on import."""
    from .image import flux_pro, dalle3, stable_diffusion
    from .video import lipsync, upscale, image_to_video
    from .audio import tts, music_generation, whisper
    
    # Generators register themselves when imported
    pass

# Auto-register on import
register_all_generators()
```

### Conditional Registration

```python
# generators/experimental/__init__.py
def register_experimental_generators():
    """Register experimental generators if dependencies available.""" 
    try:
        import advanced_ai_library
        from .advanced_generator import AdvancedGenerator
        registry.register(AdvancedGenerator())
        print("Registered advanced generator")
    except ImportError:
        print("Advanced generator not available - missing dependencies")

if os.getenv("ENABLE_EXPERIMENTAL", "false").lower() == "true":
    register_experimental_generators()
```

### Plugin-Style Registration

```python
# plugins/custom_generators.py
class CustomGeneratorPlugin:
    """Plugin that provides custom generators."""
    
    def __init__(self):
        self.generators = [
            MyCustomGenerator(),
            AnotherCustomGenerator()
        ]
    
    def register(self, registry):
        """Register all generators with the provided registry."""
        for generator in self.generators:
            registry.register(generator)
            print(f"Registered {generator.name}")
    
    def unregister(self, registry):
        """Unregister all generators."""
        for generator in self.generators:
            registry.unregister(generator.name)

# Usage
plugin = CustomGeneratorPlugin()
plugin.register(registry)
```

These examples demonstrate the flexibility and power of the Boards generator system, showing how to create generators for different media types, handle complex inputs, and implement advanced features like batch processing and conditional logic!
