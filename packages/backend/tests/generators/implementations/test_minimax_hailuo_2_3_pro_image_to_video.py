"""
Tests for FalMinimaxHailuo23ProImageToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.minimax_hailuo_2_3_pro_image_to_video import (
    FalMinimaxHailuo23ProImageToVideoGenerator,
    MinimaxHailuo23ProImageToVideoInput,
)


class TestMinimaxHailuo23ProImageToVideoInput:
    """Tests for MinimaxHailuo23ProImageToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="A beautiful sunset over the ocean with gentle waves",
            image_url=image,
            prompt_optimizer=True,
        )

        assert input_data.prompt == "A beautiful sunset over the ocean with gentle waves"
        assert input_data.image_url == image
        assert input_data.prompt_optimizer is True

    def test_input_defaults(self):
        """Test default values."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="Test prompt",
            image_url=image,
        )

        assert input_data.prompt_optimizer is True

    def test_prompt_length_validation(self):
        """Test prompt length validation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test empty prompt (min_length=1)
        with pytest.raises(ValidationError):
            MinimaxHailuo23ProImageToVideoInput(
                prompt="",
                image_url=image,
            )

        # Test valid prompt at minimum length
        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="A",
            image_url=image,
        )
        assert input_data.prompt == "A"

        # Test valid prompt at maximum length (2000 chars)
        long_prompt = "A" * 2000
        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt=long_prompt,
            image_url=image,
        )
        assert len(input_data.prompt) == 2000

        # Test prompt exceeding maximum length
        with pytest.raises(ValidationError):
            MinimaxHailuo23ProImageToVideoInput(
                prompt="A" * 2001,
                image_url=image,
            )

    def test_prompt_optimizer_options(self):
        """Test prompt optimizer can be enabled or disabled."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test with optimizer enabled
        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="Test prompt",
            image_url=image,
            prompt_optimizer=True,
        )
        assert input_data.prompt_optimizer is True

        # Test with optimizer disabled
        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="Test prompt",
            image_url=image,
            prompt_optimizer=False,
        )
        assert input_data.prompt_optimizer is False


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalMinimaxHailuo23ProImageToVideoGenerator:
    """Tests for FalMinimaxHailuo23ProImageToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalMinimaxHailuo23ProImageToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-minimax-hailuo-2-3-pro-image-to-video"
        assert self.generator.artifact_type == "video"
        assert "MiniMax" in self.generator.description
        assert "Hailuo" in self.generator.description
        assert "1080p" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == MinimaxHailuo23ProImageToVideoInput

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

            input_data = MinimaxHailuo23ProImageToVideoInput(
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
    async def test_generate_successful(self):
        """Test successful generation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="A cinematic shot of a beautiful landscape",
            image_url=image,
            prompt_optimizer=True,
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
                    }
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
                duration=None,
                format="mp4",
                fps=None,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_input.png"

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

            # Verify API call with correct arguments
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/minimax/hailuo-2.3/pro/image-to-video",
                arguments={
                    "prompt": "A cinematic shot of a beautiful landscape",
                    "image_url": fake_uploaded_image,
                    "prompt_optimizer": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_optimizer_disabled(self):
        """Test generation with prompt optimizer disabled."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="Test prompt",
            image_url=image,
            prompt_optimizer=False,
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
                width=1920,
                height=1080,
                duration=None,
                format="mp4",
                fps=None,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_input.png"

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

            # Verify API call arguments include optimizer disabled
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["prompt_optimizer"] is False

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

        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="test",
            image_url=image,
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
                    return "/tmp/fake_input.png"

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
    async def test_estimate_cost(self):
        """Test cost estimation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = MinimaxHailuo23ProImageToVideoInput(
            prompt="Test prompt",
            image_url=image,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost for 1080p video generation
        assert cost == 0.12
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = MinimaxHailuo23ProImageToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_url" in schema["properties"]
        assert "prompt_optimizer" in schema["properties"]

        # Check that required fields are marked
        assert set(schema["required"]) == {"prompt", "image_url"}

        # Check defaults
        prompt_optimizer_prop = schema["properties"]["prompt_optimizer"]
        assert prompt_optimizer_prop["default"] is True

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 2000
