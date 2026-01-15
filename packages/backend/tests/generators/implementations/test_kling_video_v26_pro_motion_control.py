"""
Tests for FalKlingVideoV26ProMotionControlGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.kling_video_v26_pro_motion_control import (
    FalKlingVideoV26ProMotionControlGenerator,
    KlingVideoV26ProMotionControlInput,
)


class TestKlingVideoV26ProMotionControlInput:
    """Tests for KlingVideoV26ProMotionControlInput schema."""

    def test_valid_input_minimal(self):
        """Test valid input creation with required fields only."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1920,
            height=1080,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30,
        )

        input_data = KlingVideoV26ProMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
        )

        assert input_data.image_url == image_artifact
        assert input_data.video_url == video_artifact
        assert input_data.character_orientation == "image"
        assert input_data.prompt is None
        assert input_data.keep_original_sound is True

    def test_valid_input_full(self):
        """Test valid input creation with all fields."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1920,
            height=1080,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=10.0,
            fps=30,
        )

        input_data = KlingVideoV26ProMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="video",
            prompt="Dancing motion with expressive gestures",
            keep_original_sound=False,
        )

        assert input_data.image_url == image_artifact
        assert input_data.video_url == video_artifact
        assert input_data.character_orientation == "video"
        assert input_data.prompt == "Dancing motion with expressive gestures"
        assert input_data.keep_original_sound is False

    def test_input_defaults(self):
        """Test default values."""
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
            duration=5.0,
            fps=30,
        )

        input_data = KlingVideoV26ProMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
        )

        assert input_data.prompt is None
        assert input_data.keep_original_sound is True

    def test_invalid_character_orientation(self):
        """Test validation fails for invalid character_orientation."""
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
            duration=5.0,
            fps=30,
        )

        with pytest.raises(ValidationError):
            KlingVideoV26ProMotionControlInput(
                image_url=image_artifact,
                video_url=video_artifact,
                character_orientation="invalid",  # type: ignore[arg-type]
            )

    def test_all_character_orientation_options(self):
        """Test all valid character_orientation options."""
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
            duration=5.0,
            fps=30,
        )

        valid_orientations = ["image", "video"]

        for orientation in valid_orientations:
            input_data = KlingVideoV26ProMotionControlInput(
                image_url=image_artifact,
                video_url=video_artifact,
                character_orientation=orientation,  # type: ignore[arg-type]
            )
            assert input_data.character_orientation == orientation

    def test_prompt_max_length(self):
        """Test prompt max length validation."""
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
            duration=5.0,
            fps=30,
        )

        # This should succeed (exactly at limit)
        long_prompt = "a" * 2500
        input_data = KlingVideoV26ProMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
            prompt=long_prompt,
        )
        assert len(input_data.prompt) == 2500  # type: ignore[arg-type]

        # This should fail (over limit)
        too_long_prompt = "a" * 2501
        with pytest.raises(ValidationError):
            KlingVideoV26ProMotionControlInput(
                image_url=image_artifact,
                video_url=video_artifact,
                character_orientation="image",
                prompt=too_long_prompt,
            )


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalKlingVideoV26ProMotionControlGenerator:
    """Tests for FalKlingVideoV26ProMotionControlGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalKlingVideoV26ProMotionControlGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-kling-video-v26-pro-motion-control"
        assert self.generator.artifact_type == "video"
        assert "motion" in self.generator.description.lower()
        assert "Kling" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == KlingVideoV26ProMotionControlInput

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
                duration=5.0,
                fps=30,
            )

            input_data = KlingVideoV26ProMotionControlInput(
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
                        fps=30,
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
    async def test_generate_successful_image_orientation(self):
        """Test successful generation with image orientation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/input.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=8.0,
            fps=30,
        )

        input_data = KlingVideoV26ProMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
            prompt="Apply dance moves",
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

            # Mock file upload
            upload_count = 0

            async def mock_upload(file_path):
                nonlocal upload_count
                upload_count += 1
                if upload_count == 1:
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

            # Verify file uploads were called (image + video)
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API call
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/kling-video/v2.6/pro/motion-control",
                arguments={
                    "image_url": fake_uploaded_image,
                    "video_url": fake_uploaded_video,
                    "character_orientation": "image",
                    "keep_original_sound": True,
                    "prompt": "Apply dance moves",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_video_orientation(self):
        """Test successful generation with video orientation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/input.png",
            format="png",
            width=1080,
            height=1920,
        )
        video_artifact = VideoArtifact(
            generation_id="gen2",
            storage_url="https://example.com/input.mp4",
            format="mp4",
            width=1080,
            height=1920,
            duration=15.0,
            fps=30,
        )

        input_data = KlingVideoV26ProMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="video",
            keep_original_sound=False,
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output_video.mp4"

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
                return "https://fal.media/uploaded.file"

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1080,
                height=1920,
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

            # Verify API call with video orientation and keep_original_sound=False
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["character_orientation"] == "video"
            assert call_args[1]["arguments"]["keep_original_sound"] is False

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
            storage_url="https://example.com/input.mp4",
            format="mp4",
            width=1024,
            height=768,
            duration=5.0,
            fps=30,
        )

        input_data = KlingVideoV26ProMotionControlInput(
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
                return "https://fal.media/uploaded.file"

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
    async def test_estimate_cost(self):
        """Test cost estimation."""
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
            duration=5.0,
            fps=30,
        )

        input_data = KlingVideoV26ProMotionControlInput(
            image_url=image_artifact,
            video_url=video_artifact,
            character_orientation="image",
        )

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.15
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = KlingVideoV26ProMotionControlInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image_url" in schema["properties"]
        assert "video_url" in schema["properties"]
        assert "character_orientation" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "keep_original_sound" in schema["properties"]

        # Check prompt constraints (prompt is optional, so check anyOf structure)
        prompt_prop = schema["properties"]["prompt"]
        # Optional fields have anyOf structure in Pydantic v2
        if "anyOf" in prompt_prop:
            # Find the non-null type in anyOf
            string_schema = next(
                (s for s in prompt_prop["anyOf"] if s.get("type") == "string"), None
            )
            assert string_schema is not None
            assert string_schema.get("maxLength") == 2500
        else:
            assert prompt_prop.get("maxLength") == 2500

        # Check character_orientation enum
        char_orient_prop = schema["properties"]["character_orientation"]
        assert "enum" in char_orient_prop or "anyOf" in char_orient_prop

        # Check keep_original_sound default
        keep_sound_prop = schema["properties"]["keep_original_sound"]
        assert keep_sound_prop.get("default") is True
