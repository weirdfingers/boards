"""
Tests for FalWan25PreviewImageToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.wan_25_preview_image_to_video import (
    FalWan25PreviewImageToVideoGenerator,
    Wan25PreviewImageToVideoInput,
)


class TestWan25PreviewImageToVideoInput:
    """Tests for Wan25PreviewImageToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )

        prompt = "A stylish woman walks down a Tokyo street filled with warm glowing neon"
        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt=prompt,
            duration="10",
            resolution="1080p",
            seed=42,
            negative_prompt="blurry, distorted",
            enable_prompt_expansion=True,
            enable_safety_checker=True,
        )

        assert input_data.prompt == prompt
        assert input_data.image == image
        assert input_data.duration == "10"
        assert input_data.resolution == "1080p"
        assert input_data.seed == 42
        assert input_data.negative_prompt == "blurry, distorted"
        assert input_data.enable_prompt_expansion is True
        assert input_data.enable_safety_checker is True

    def test_input_defaults(self):
        """Test default values."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
        )

        assert input_data.duration == "5"
        assert input_data.resolution == "1080p"
        assert input_data.seed is None
        assert input_data.negative_prompt is None
        assert input_data.audio_url is None
        assert input_data.enable_prompt_expansion is True
        assert input_data.enable_safety_checker is True

    def test_duration_values(self):
        """Test that duration accepts valid values."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test 5 seconds
        input_data_5 = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            duration="5",
        )
        assert input_data_5.duration == "5"

        # Test 10 seconds
        input_data_10 = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            duration="10",
        )
        assert input_data_10.duration == "10"

    def test_resolution_values(self):
        """Test that resolution accepts valid values."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        for resolution in ["480p", "720p", "1080p"]:
            input_data = Wan25PreviewImageToVideoInput(
                image=image,
                prompt="Test prompt",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_seed_optional(self):
        """Test that seed can be None."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            seed=None,
        )

        assert input_data.seed is None

    def test_audio_url_optional(self):
        """Test that audio_url can be provided."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            audio_url="https://example.com/background.mp3",
        )

        assert input_data.audio_url == "https://example.com/background.mp3"

    def test_prompt_expansion_disabled(self):
        """Test that prompt expansion can be disabled."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            enable_prompt_expansion=False,
        )

        assert input_data.enable_prompt_expansion is False

    def test_safety_checker_disabled(self):
        """Test that safety checker can be disabled."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            enable_safety_checker=False,
        )

        assert input_data.enable_safety_checker is False


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalWan25PreviewImageToVideoGenerator:
    """Tests for FalWan25PreviewImageToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalWan25PreviewImageToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-wan-25-preview-image-to-video"
        assert self.generator.artifact_type == "video"
        assert "WAN 2.5" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Wan25PreviewImageToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/input.png",
                format="png",
                width=1024,
                height=768,
            )

            input_data = Wan25PreviewImageToVideoInput(
                image=image,
                prompt="Test prompt",
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
    async def test_generate_successful(self):
        """Test successful generation with default parameters."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="cinematic camera movement through a vibrant city",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image = "https://fal.media/files/input.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler with async iterator for events
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"

            # Create async iterator that yields nothing (no events)
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

            # Mock the get() method to return result
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
                        "file_size": 2048000,
                        "width": 1920,
                        "height": 1080,
                        "fps": 30,
                        "duration": 5,
                    },
                    "seed": 12345,
                    "actual_prompt": "expanded prompt",
                }
            )

            # Mock file upload
            async def mock_upload(file_path):
                return fake_uploaded_image

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1920,
                height=1080,
                duration=5,
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

            # Verify API call arguments
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/wan-25-preview/image-to-video",
                arguments={
                    "image_url": fake_uploaded_image,
                    "prompt": "cinematic camera movement through a vibrant city",
                    "duration": "5",
                    "resolution": "1080p",
                    "enable_prompt_expansion": True,
                    "enable_safety_checker": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_all_parameters(self):
        """Test successful generation with all parameters."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            duration="10",
            resolution="720p",
            seed=12345,
            negative_prompt="blurry, low quality",
            audio_url="https://example.com/music.mp3",
            enable_prompt_expansion=False,
            enable_safety_checker=False,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image = "https://fal.media/files/input.png"

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
                        "width": 1280,
                        "height": 720,
                        "fps": 30,
                        "duration": 10,
                    }
                }
            )

            async def mock_upload(file_path):
                return fake_uploaded_image

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                duration=10,
                format="mp4",
                fps=30,
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

            # Verify API call includes all parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 12345
            assert call_args[1]["arguments"]["negative_prompt"] == "blurry, low quality"
            assert call_args[1]["arguments"]["audio_url"] == "https://example.com/music.mp3"
            assert call_args[1]["arguments"]["duration"] == "10"
            assert call_args[1]["arguments"]["resolution"] == "720p"
            assert call_args[1]["arguments"]["enable_prompt_expansion"] is False
            assert call_args[1]["arguments"]["enable_safety_checker"] is False

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="test",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video field

            fake_uploaded_image = "https://fal.media/files/input.png"

            async def mock_upload(file_path):
                return fake_uploaded_image

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
    async def test_estimate_cost_5_seconds(self):
        """Test cost estimation for 5 second video."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            duration="5",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost for 5 seconds
        assert cost == 0.10
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_10_seconds(self):
        """Test cost estimation for 10 second video."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = Wan25PreviewImageToVideoInput(
            image=image,
            prompt="Test prompt",
            duration="10",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Double cost for 10 seconds
        assert cost == 0.20
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Wan25PreviewImageToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "audio_url" in schema["properties"]
        assert "enable_prompt_expansion" in schema["properties"]
        assert "enable_safety_checker" in schema["properties"]

        # Check that required fields are marked
        assert set(schema["required"]) == {"image", "prompt"}

        # Check defaults
        assert schema["properties"]["duration"]["default"] == "5"
        assert schema["properties"]["resolution"]["default"] == "1080p"
        assert schema["properties"]["enable_prompt_expansion"]["default"] is True
        assert schema["properties"]["enable_safety_checker"]["default"] is True
