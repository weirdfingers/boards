"""
Tests for FalSora2ImageToVideoProGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.sora_2_image_to_video_pro import (
    FalSora2ImageToVideoProGenerator,
    Sora2ImageToVideoProInput,
)


class TestSora2ImageToVideoProInput:
    """Tests for Sora2ImageToVideoProInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="A cinematic video with dramatic lighting",
            image_url=image,
            resolution="1080p",
            aspect_ratio="16:9",
            duration=8,
        )

        assert input_data.prompt == "A cinematic video with dramatic lighting"
        assert input_data.image_url == image
        assert input_data.resolution == "1080p"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.duration == 8

    def test_input_defaults(self):
        """Test default values."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="Test prompt",
            image_url=image,
        )

        assert input_data.resolution == "auto"
        assert input_data.aspect_ratio == "auto"
        assert input_data.duration == 4

    def test_prompt_length_validation(self):
        """Test prompt length validation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test empty prompt fails
        with pytest.raises(ValidationError):
            Sora2ImageToVideoProInput(
                prompt="",
                image_url=image,
            )

        # Test prompt exceeding max length fails
        with pytest.raises(ValidationError):
            Sora2ImageToVideoProInput(
                prompt="x" * 5001,  # Exceeds 5000 char limit
                image_url=image,
            )

        # Test valid prompt at max length succeeds
        input_data = Sora2ImageToVideoProInput(
            prompt="x" * 5000,
            image_url=image,
        )
        assert len(input_data.prompt) == 5000

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            Sora2ImageToVideoProInput(
                prompt="Test",
                image_url=image,
                resolution="4k",  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            Sora2ImageToVideoProInput(
                prompt="Test",
                image_url=image,
                aspect_ratio="4:3",  # type: ignore[arg-type]
            )

    def test_invalid_duration(self):
        """Test validation fails for invalid duration."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            Sora2ImageToVideoProInput(
                prompt="Test",
                image_url=image,
                duration=6,  # type: ignore[arg-type]  # Only 4, 8, 12 allowed
            )

    def test_resolution_options(self):
        """Test all valid resolution options."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_resolutions = ["auto", "720p", "1080p"]

        for resolution in valid_resolutions:
            input_data = Sora2ImageToVideoProInput(
                prompt="Test",
                image_url=image,
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_ratios = ["auto", "9:16", "16:9"]

        for ratio in valid_ratios:
            input_data = Sora2ImageToVideoProInput(
                prompt="Test",
                image_url=image,
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_duration_options(self):
        """Test all valid duration options."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_durations = [4, 8, 12]

        for duration in valid_durations:
            input_data = Sora2ImageToVideoProInput(
                prompt="Test",
                image_url=image,
                duration=duration,  # type: ignore[arg-type]
            )
            assert input_data.duration == duration


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalSora2ImageToVideoProGenerator:
    """Tests for FalSora2ImageToVideoProGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalSora2ImageToVideoProGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-sora-2-image-to-video-pro"
        assert self.generator.artifact_type == "video"
        assert "Sora 2" in self.generator.description
        assert "video" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Sora2ImageToVideoProInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=1024,
                height=768,
            )

            input_data = Sora2ImageToVideoProInput(
                prompt="Test prompt",
                image_url=image,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return VideoArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        width=1,
                        height=1,
                        duration=1,
                        format="mp4",
                        fps=None,
                    )

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="FAL_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful_4s(self):
        """Test successful generation with 4 second duration."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1280,
            height=720,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="A cinematic pan across a beautiful landscape",
            image_url=image,
            resolution="720p",
            aspect_ratio="16:9",
            duration=4,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/sora-output.mp4"
        fake_uploaded_url = "https://fal.media/files/image.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler with async iterator for events
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"

            # Create async iterator that yields nothing (no events)
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

            # Mock the get() method to return result with video metadata
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                        "width": 1280,
                        "height": 720,
                        "duration": 4,
                        "fps": 30,
                        "file_size": 2048000,
                    }
                }
            )

            # Mock file upload
            async def mock_upload(file_path):
                return fake_uploaded_url

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                duration=4,
                format="mp4",
                fps=30,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_image.png"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_artifact

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify file upload was called
            assert mock_fal_client.upload_file_async.call_count == 1

            # Verify API call with uploaded URL
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/sora-2/image-to-video/pro",
                arguments={
                    "prompt": "A cinematic pan across a beautiful landscape",
                    "image_url": fake_uploaded_url,
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                    "duration": 4,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_12s(self):
        """Test successful generation with 12 second duration."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="Extended dramatic sequence",
            image_url=image,
            resolution="1080p",
            aspect_ratio="auto",
            duration=12,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/sora-output.mp4"
        fake_uploaded_url = "https://fal.media/files/image.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                        "width": 1920,
                        "height": 1080,
                        "duration": 12,
                        "fps": 24,
                    }
                }
            )

            async def mock_upload(file_path):
                return fake_uploaded_url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1920,
                height=1080,
                duration=12,
                format="mp4",
                fps=24,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_image.png"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_artifact

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify API call arguments
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["duration"] == 12
            assert call_args[1]["arguments"]["resolution"] == "1080p"

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="test",
            image_url=image,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video field

            fake_uploaded_url = "https://fal.media/files/image.png"

            async def mock_upload(file_path):
                return fake_uploaded_url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_image.png"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="No video returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_no_video_url(self):
        """Test generation fails when video object missing URL."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="test",
            image_url=image,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-999"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            # Video object exists but missing URL
            mock_handler.get = AsyncMock(return_value={"video": {"content_type": "video/mp4"}})

            fake_uploaded_url = "https://fal.media/files/image.png"

            async def mock_upload(file_path):
                return fake_uploaded_url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_image.png"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="Video missing URL"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_4s(self):
        """Test cost estimation for 4 second duration (base cost)."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="Test prompt",
            image_url=image,
            duration=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost for 4 seconds
        assert cost == 0.50
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_8s(self):
        """Test cost estimation for 8 second duration (2x base)."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="Test prompt",
            image_url=image,
            duration=8,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 2x base cost for 8 seconds
        assert cost == 1.00
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_12s(self):
        """Test cost estimation for 12 second duration (3x base)."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Sora2ImageToVideoProInput(
            prompt="Test prompt",
            image_url=image,
            duration=12,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 3x base cost for 12 seconds
        assert cost == 1.50
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Sora2ImageToVideoProInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_url" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "duration" in schema["properties"]

        # Check that required fields are marked
        assert set(schema["required"]) == {"prompt", "image_url"}

        # Check defaults
        resolution_prop = schema["properties"]["resolution"]
        assert resolution_prop["default"] == "auto"

        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert aspect_ratio_prop["default"] == "auto"

        duration_prop = schema["properties"]["duration"]
        assert duration_prop["default"] == 4

        # Check prompt validation
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 5000
