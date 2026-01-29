"""
Tests for FalKlingMotionControlGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.kling_motion_control import (
    FalKlingMotionControlGenerator,
    KlingMotionControlInput,
)


class TestKlingMotionControlInput:
    """Tests for KlingMotionControlInput schema."""

    @pytest.fixture
    def sample_image_artifact(self):
        """Provide a sample image artifact."""
        return ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1920,
            height=1080,
        )

    @pytest.fixture
    def sample_video_artifact(self):
        """Provide a sample video artifact."""
        return VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=10.0,
            fps=30.0,
        )

    def test_valid_input_with_all_fields(self, sample_image_artifact, sample_video_artifact):
        """Test valid input creation with all fields."""
        input_data = KlingMotionControlInput(
            image_url=sample_image_artifact,
            video_url=sample_video_artifact,
            character_orientation="video",
            prompt="An african american woman dancing",
            keep_original_sound=False,
        )

        assert input_data.image_url == sample_image_artifact
        assert input_data.video_url == sample_video_artifact
        assert input_data.character_orientation == "video"
        assert input_data.prompt == "An african american woman dancing"
        assert input_data.keep_original_sound is False

    def test_valid_input_with_required_fields_only(
        self, sample_image_artifact, sample_video_artifact
    ):
        """Test valid input with only required fields."""
        input_data = KlingMotionControlInput(
            image_url=sample_image_artifact,
            video_url=sample_video_artifact,
            character_orientation="image",
        )

        assert input_data.image_url == sample_image_artifact
        assert input_data.video_url == sample_video_artifact
        assert input_data.character_orientation == "image"
        assert input_data.prompt is None
        assert input_data.keep_original_sound is True

    def test_input_defaults(self, sample_image_artifact, sample_video_artifact):
        """Test default values."""
        input_data = KlingMotionControlInput(
            image_url=sample_image_artifact,
            video_url=sample_video_artifact,
            character_orientation="video",
        )

        assert input_data.prompt is None
        assert input_data.keep_original_sound is True

    def test_invalid_character_orientation(self, sample_image_artifact, sample_video_artifact):
        """Test validation fails for invalid character_orientation."""
        with pytest.raises(ValidationError):
            KlingMotionControlInput(
                image_url=sample_image_artifact,
                video_url=sample_video_artifact,
                character_orientation="invalid",  # type: ignore[arg-type]
            )

    def test_all_character_orientation_options(
        self, sample_image_artifact, sample_video_artifact
    ):
        """Test all valid character_orientation options."""
        valid_orientations = ["image", "video"]

        for orientation in valid_orientations:
            input_data = KlingMotionControlInput(
                image_url=sample_image_artifact,
                video_url=sample_video_artifact,
                character_orientation=orientation,  # type: ignore[arg-type]
            )
            assert input_data.character_orientation == orientation

    def test_prompt_max_length(self, sample_image_artifact, sample_video_artifact):
        """Test prompt max length validation."""
        # This should succeed (exactly at limit)
        long_prompt = "a" * 2500
        input_data = KlingMotionControlInput(
            image_url=sample_image_artifact,
            video_url=sample_video_artifact,
            character_orientation="image",
            prompt=long_prompt,
        )
        assert input_data.prompt is not None
        assert len(input_data.prompt) == 2500

        # This should fail (over limit)
        too_long_prompt = "a" * 2501
        with pytest.raises(ValidationError):
            KlingMotionControlInput(
                image_url=sample_image_artifact,
                video_url=sample_video_artifact,
                character_orientation="image",
                prompt=too_long_prompt,
            )

    def test_missing_required_image_url(self, sample_video_artifact):
        """Test validation fails when image_url is missing."""
        with pytest.raises(ValidationError):
            KlingMotionControlInput(
                video_url=sample_video_artifact,
                character_orientation="image",
            )  # type: ignore[call-arg]

    def test_missing_required_video_url(self, sample_image_artifact):
        """Test validation fails when video_url is missing."""
        with pytest.raises(ValidationError):
            KlingMotionControlInput(
                image_url=sample_image_artifact,
                character_orientation="image",
            )  # type: ignore[call-arg]

    def test_missing_required_character_orientation(
        self, sample_image_artifact, sample_video_artifact
    ):
        """Test validation fails when character_orientation is missing."""
        with pytest.raises(ValidationError):
            KlingMotionControlInput(
                image_url=sample_image_artifact,
                video_url=sample_video_artifact,
            )  # type: ignore[call-arg]


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalKlingMotionControlGenerator:
    """Tests for FalKlingMotionControlGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalKlingMotionControlGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-kling-motion-control"
        assert self.generator.artifact_type == "video"
        assert "motion" in self.generator.description.lower()
        assert "Kling" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == KlingMotionControlInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=1024,
                height=768,
            )
            video_artifact = VideoArtifact(
                generation_id="gen2",
                storage_url="https://example.com/video.mp4",
                format="mp4",
                width=1024,
                height=768,
                duration=10.0,
                fps=30.0,
            )

            input_data = KlingMotionControlInput(
                image_url=image_artifact,
                video_url=video_artifact,
                character_orientation="image",
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
                        format="mp4",
                        duration=5.0,
                        fps=30.0,
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
    async def test_generate_successful_image_mode(self):
        """Test successful generation with image orientation mode."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/motion.mp4",
            format="mp4",
            width=1280,
            height=720,
            duration=8.0,
            fps=30.0,
        )

        input_data = KlingMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
            prompt="A person dancing gracefully",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image = "https://fal.media/uploaded_image.png"
        fake_uploaded_video = "https://fal.media/uploaded_video.mp4"

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
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
                    }
                }
            )

            # Track upload calls to return different URLs
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                upload_call_count += 1
                if upload_call_count == 1:
                    return fake_uploaded_image
                return fake_uploaded_video

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1920,
                height=1080,
                format="mp4",
                duration=8.0,
                fps=30,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    if isinstance(artifact, ImageArtifact):
                        return "/tmp/fake_image.png"
                    return "/tmp/fake_video.mp4"

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

            # Verify file uploads were called (once for image, once for video)
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API call
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/kling-video/v2.6/standard/motion-control",
                arguments={
                    "image_url": fake_uploaded_image,
                    "video_url": fake_uploaded_video,
                    "character_orientation": "image",
                    "keep_original_sound": True,
                    "prompt": "A person dancing gracefully",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_video_mode(self):
        """Test successful generation with video orientation mode."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1080,
            height=1920,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/motion.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=15.0,
            fps=30.0,
        )

        input_data = KlingMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="video",
            keep_original_sound=False,
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output_30s.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                    }
                }
            )

            async def mock_upload(file_path):
                return "https://fal.media/uploaded_file.mp4"

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1920,
                height=1080,
                format="mp4",
                duration=15.0,
                fps=30,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_file"

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

            # Verify API call with video mode parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["character_orientation"] == "video"
            assert call_args[1]["arguments"]["keep_original_sound"] is False
            # No prompt in this test
            assert "prompt" not in call_args[1]["arguments"]

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1024,
            height=768,
            duration=5.0,
            fps=30.0,
        )

        input_data = KlingMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-error"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video in response

            async def mock_upload(file_path):
                return "https://fal.media/uploaded_file"

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
                    return "/tmp/fake_file"

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
    async def test_estimate_cost_image_mode(self):
        """Test cost estimation for image orientation mode."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1024,
            height=768,
            duration=10.0,
            fps=30.0,
        )

        input_data = KlingMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Image mode: base cost * 1.0
        assert cost == 0.12
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_video_mode(self):
        """Test cost estimation for video orientation mode."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1024,
            height=768,
            duration=20.0,
            fps=30.0,
        )

        input_data = KlingMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="video",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Video mode: base cost * 2.0
        assert cost == 0.24
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = KlingMotionControlInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image_url" in schema["properties"]
        assert "video_url" in schema["properties"]
        assert "character_orientation" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "keep_original_sound" in schema["properties"]

        # Check character_orientation enum
        orientation_prop = schema["properties"]["character_orientation"]
        assert "enum" in orientation_prop or "anyOf" in orientation_prop

        # Check keep_original_sound default
        keep_sound_prop = schema["properties"]["keep_original_sound"]
        assert keep_sound_prop["default"] is True

        # Check required fields
        assert "image_url" in schema.get("required", [])
        assert "video_url" in schema.get("required", [])
        assert "character_orientation" in schema.get("required", [])
