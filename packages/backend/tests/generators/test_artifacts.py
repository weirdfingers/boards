"""
Tests for artifact type definitions.
"""

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import (
    AudioArtifact,
    ImageArtifact,
    LoRArtifact,
    TextArtifact,
    VideoArtifact,
)


class TestAudioArtifact:
    """Tests for AudioArtifact."""

    def test_valid_audio_artifact(self):
        """Test creating a valid audio artifact."""
        artifact = AudioArtifact(
            generation_id="gen_123",
            storage_url="https://example.com/audio.mp3",
            duration=120.5,
            format="mp3",
            sample_rate=44100,
            channels=2,
        )

        assert artifact.generation_id == "gen_123"
        assert artifact.storage_url == "https://example.com/audio.mp3"
        assert artifact.duration == 120.5
        assert artifact.format == "mp3"
        assert artifact.sample_rate == 44100
        assert artifact.channels == 2

    def test_audio_artifact_minimal(self):
        """Test creating audio artifact with only required fields."""
        artifact = AudioArtifact(  # type: ignore
            generation_id="gen_123",
            storage_url="https://example.com/audio.mp3",
            format="mp3",
        )

        assert artifact.generation_id == "gen_123"
        assert artifact.storage_url == "https://example.com/audio.mp3"
        assert artifact.format == "mp3"
        assert artifact.duration is None
        assert artifact.sample_rate is None
        assert artifact.channels is None


class TestVideoArtifact:
    """Tests for VideoArtifact."""

    def test_valid_video_artifact(self):
        """Test creating a valid video artifact."""
        artifact = VideoArtifact(
            generation_id="gen_456",
            storage_url="https://example.com/video.mp4",
            duration=180.0,
            width=1920,
            height=1080,
            format="mp4",
            fps=30.0,
        )

        assert artifact.generation_id == "gen_456"
        assert artifact.storage_url == "https://example.com/video.mp4"
        assert artifact.duration == 180.0
        assert artifact.width == 1920
        assert artifact.height == 1080
        assert artifact.format == "mp4"
        assert artifact.fps == 30.0

    def test_video_artifact_required_fields(self):
        """Test video artifact with only required fields."""
        artifact = VideoArtifact(  # type: ignore
            generation_id="gen_456",
            storage_url="https://example.com/video.mp4",
            width=1920,
            height=1080,
            format="mp4",
        )

        assert artifact.width == 1920
        assert artifact.height == 1080
        assert artifact.format == "mp4"
        assert artifact.duration is None
        assert artifact.fps is None


class TestImageArtifact:
    """Tests for ImageArtifact."""

    def test_valid_image_artifact(self):
        """Test creating a valid image artifact."""
        artifact = ImageArtifact(
            generation_id="gen_789",
            storage_url="https://example.com/image.png",
            width=1024,
            height=1024,
            format="png",
        )

        assert artifact.generation_id == "gen_789"
        assert artifact.storage_url == "https://example.com/image.png"
        assert artifact.width == 1024
        assert artifact.height == 1024
        assert artifact.format == "png"


class TestTextArtifact:
    """Tests for TextArtifact."""

    def test_valid_text_artifact(self):
        """Test creating a valid text artifact."""
        artifact = TextArtifact(
            generation_id="gen_text",
            content="This is generated text content.",
            format="plain",
            storage_url="",
        )

        assert artifact.generation_id == "gen_text"
        assert artifact.content == "This is generated text content."
        assert artifact.format == "plain"

    def test_text_artifact_default_format(self):
        """Test text artifact uses default format."""
        artifact = TextArtifact(
            generation_id="gen_text", content="Content", storage_url="", format="plain"
        )

        assert artifact.format == "plain"


class TestLoRArtifact:
    """Tests for LoRArtifact."""

    def test_valid_lora_artifact(self):
        """Test creating a valid LoRA artifact."""
        artifact = LoRArtifact(
            generation_id="gen_lora",
            storage_url="https://example.com/model.safetensors",
            base_model="stable-diffusion-v1-5",
            format="safetensors",
            trigger_words=["trigger1", "trigger2"],
        )

        assert artifact.generation_id == "gen_lora"
        assert artifact.storage_url == "https://example.com/model.safetensors"
        assert artifact.base_model == "stable-diffusion-v1-5"
        assert artifact.format == "safetensors"
        assert artifact.trigger_words == ["trigger1", "trigger2"]

    def test_lora_artifact_no_trigger_words(self):
        """Test LoRA artifact without trigger words."""
        artifact = LoRArtifact(  # type: ignore
            generation_id="gen_lora",
            storage_url="https://example.com/model.safetensors",
            base_model="stable-diffusion-v1-5",
            format="safetensors",
        )

        assert artifact.trigger_words is None


class TestArtifactValidation:
    """Tests for artifact validation."""

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            ImageArtifact()  # type: ignore  # Missing all required fields

    def test_json_serialization(self):
        """Test artifacts can be serialized to JSON."""
        artifact = ImageArtifact(
            generation_id="gen_123",
            storage_url="https://example.com/image.png",
            width=512,
            height=512,
            format="png",
        )

        json_data = artifact.model_dump()
        assert json_data["generation_id"] == "gen_123"
        assert json_data["width"] == 512
        assert json_data["height"] == 512

    def test_json_schema_generation(self):
        """Test artifacts can generate JSON schema."""
        schema = ImageArtifact.model_json_schema()

        assert schema["type"] == "object"
        assert "generation_id" in schema["properties"]
        assert "storage_url" in schema["properties"]
        assert "width" in schema["properties"]
        assert "height" in schema["properties"]
        assert "format" in schema["properties"]

        # Check required fields
        required_fields = schema["required"]
        assert "generation_id" in required_fields
        assert "storage_url" in required_fields
        assert "width" in required_fields
        assert "height" in required_fields
        assert "format" in required_fields
