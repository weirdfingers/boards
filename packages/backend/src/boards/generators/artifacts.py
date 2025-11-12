"""
Artifact type definitions for the Boards generators system.

These Pydantic models represent different types of generated content
that can be used as inputs and outputs for generators.
"""

from pydantic import BaseModel, Field


class DigitalArtifact(BaseModel):
    """Represents a digital artifact from a generation."""

    generation_id: str = Field(description="ID of the generation that created this artifact")
    storage_url: str = Field(description="URL where the digital file is stored")
    format: str = Field(description="Digital format (png, jpg, webp, etc.)")


class AudioArtifact(DigitalArtifact):
    """Represents an audio file artifact from a generation."""

    duration: float | None = Field(None, description="Duration in seconds")
    sample_rate: int | None = Field(None, description="Sample rate in Hz")
    channels: int | None = Field(None, description="Number of audio channels")


class VideoArtifact(DigitalArtifact):
    """Represents a video file artifact from a generation."""

    duration: float | None = Field(None, description="Duration in seconds")
    width: int | None = Field(None, description="Video width in pixels")
    height: int | None = Field(None, description="Video height in pixels")
    fps: float | None = Field(None, description="Frames per second")


class ImageArtifact(DigitalArtifact):
    """Represents an image file artifact from a generation."""

    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")


class TextArtifact(DigitalArtifact):
    """Represents a text artifact from a generation."""

    content: str = Field(description="The generated text content")


class LoRArtifact(DigitalArtifact):
    """Represents a LoRA (Low-Rank Adaptation) model artifact."""

    base_model: str = Field(description="Base model this LoRA was trained on")
    trigger_words: list[str] | None = Field(None, description="Trigger words for this LoRA")
