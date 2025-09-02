"""
Artifact type definitions for the Boards generators system.

These Pydantic models represent different types of generated content
that can be used as inputs and outputs for generators.
"""
from typing import Optional
from pydantic import BaseModel, Field


class AudioArtifact(BaseModel):
    """Represents an audio file artifact from a generation."""
    generation_id: str = Field(description="ID of the generation that created this artifact")
    storage_url: str = Field(description="URL where the audio file is stored")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    format: str = Field(description="Audio format (mp3, wav, etc.)")
    sample_rate: Optional[int] = Field(None, description="Sample rate in Hz")
    channels: Optional[int] = Field(None, description="Number of audio channels")


class VideoArtifact(BaseModel):
    """Represents a video file artifact from a generation."""
    generation_id: str = Field(description="ID of the generation that created this artifact")
    storage_url: str = Field(description="URL where the video file is stored")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    width: int = Field(description="Video width in pixels")
    height: int = Field(description="Video height in pixels")
    format: str = Field(description="Video format (mp4, webm, etc.)")
    fps: Optional[float] = Field(None, description="Frames per second")


class ImageArtifact(BaseModel):
    """Represents an image file artifact from a generation."""
    generation_id: str = Field(description="ID of the generation that created this artifact")
    storage_url: str = Field(description="URL where the image file is stored")
    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")
    format: str = Field(description="Image format (png, jpg, webp, etc.)")


class TextArtifact(BaseModel):
    """Represents a text artifact from a generation."""
    generation_id: str = Field(description="ID of the generation that created this artifact")
    content: str = Field(description="The generated text content")
    format: str = Field(default="plain", description="Text format (plain, markdown, html, etc.)")


class LoRArtifact(BaseModel):
    """Represents a LoRA (Low-Rank Adaptation) model artifact."""
    generation_id: str = Field(description="ID of the generation that created this artifact")
    storage_url: str = Field(description="URL where the LoRA file is stored")
    base_model: str = Field(description="Base model this LoRA was trained on")
    format: str = Field(description="LoRA format (safetensors, etc.)")
    trigger_words: Optional[list[str]] = Field(None, description="Trigger words for this LoRA")