"""
Tests for FalLtx23ImageToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.ltx_23_image_to_video import (
    FalLtx23ImageToVideoGenerator,
    Ltx23ImageToVideoInput,
)


def _make_image_artifact() -> ImageArtifact:
    """Create a test image artifact."""
    return ImageArtifact(
        generation_id="test_gen",
        storage_url="https://example.com/image.png",
        width=1920,
        height=1080,
        format="png",
    )


class TestLtx23ImageToVideoInput:
    """Tests for Ltx23ImageToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image = _make_image_artifact()
        input_data = Ltx23ImageToVideoInput(
            image=image,
            prompt="Animate this scene with gentle motion",
            duration=8,
            resolution="1440p",
            aspect_ratio="16:9",
            fps=48,
        )

        assert input_data.image == image
        assert input_data.prompt == "Animate this scene with gentle motion"
        assert input_data.duration == 8
        assert input_data.resolution == "1440p"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.fps == 48

    def test_input_defaults(self):
        """Test default values."""
        image = _make_image_artifact()
        input_data = Ltx23ImageToVideoInput(
            image=image,
            prompt="Test prompt",
        )

        assert input_data.end_image is None
        assert input_data.duration == 6
        assert input_data.resolution == "1080p"
        assert input_data.aspect_ratio == "auto"
        assert input_data.fps == 25
        assert input_data.generate_audio is True

    def test_invalid_duration(self):
        """Test validation fails for invalid duration."""
        with pytest.raises(ValidationError):
            Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                duration=5,  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                aspect_ratio="1:1",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        with pytest.raises(ValidationError):
            Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                resolution="720p",  # type: ignore[arg-type]
            )

    def test_invalid_fps(self):
        """Test validation fails for invalid fps."""
        with pytest.raises(ValidationError):
            Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                fps=30,  # type: ignore[arg-type]
            )

    def test_prompt_min_length(self):
        """Test prompt min length validation."""
        with pytest.raises(ValidationError):
            Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="",
            )

    def test_prompt_max_length(self):
        """Test prompt max length validation."""
        long_prompt = "a" * 5000
        input_data = Ltx23ImageToVideoInput(
            image=_make_image_artifact(),
            prompt=long_prompt,
        )
        assert len(input_data.prompt) == 5000

        too_long_prompt = "a" * 5001
        with pytest.raises(ValidationError):
            Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt=too_long_prompt,
            )

    def test_all_duration_options(self):
        """Test all valid duration options."""
        for duration in [6, 8, 10]:
            input_data = Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                duration=duration,  # type: ignore[arg-type]
            )
            assert input_data.duration == duration

    def test_all_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        for ratio in ["auto", "16:9", "9:16"]:
            input_data = Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_all_resolution_options(self):
        """Test all valid resolution options."""
        for resolution in ["1080p", "1440p", "2160p"]:
            input_data = Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_all_fps_options(self):
        """Test all valid fps options."""
        for fps in [24, 25, 48, 50]:
            input_data = Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
                prompt="Test",
                fps=fps,  # type: ignore[arg-type]
            )
            assert input_data.fps == fps

    def test_with_end_image(self):
        """Test input with end image for transitions."""
        image = _make_image_artifact()
        end_image = _make_image_artifact()
        input_data = Ltx23ImageToVideoInput(
            image=image,
            prompt="Transition between scenes",
            end_image=end_image,
        )
        assert input_data.end_image == end_image


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield


class TestFalLtx23ImageToVideoGenerator:
    """Tests for FalLtx23ImageToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalLtx23ImageToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-ltx-23-image-to-video"
        assert self.generator.artifact_type == "video"
        assert "LTX-2.3" in self.generator.description
        assert "image" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Ltx23ImageToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Ltx23ImageToVideoInput(
                image=_make_image_artifact(),
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
                        format="mp4",
                        duration=6.0,
                        fps=25,
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
    async def test_generate_successful_default(self):
        """Test successful generation with default parameters."""
        image = _make_image_artifact()
        input_data = Ltx23ImageToVideoInput(
            image=image,
            prompt="Animate this landscape with gentle wind",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image = "https://fal.ai/uploaded/image.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "width": 1920,
                        "height": 1080,
                        "duration": 6.0,
                        "fps": 25,
                    },
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
                storage_url=fake_video_url,
                width=1920,
                height=1080,
                format="mp4",
                duration=6.0,
                fps=25,
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

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            assert mock_fal_client.upload_file_async.call_count == 1

            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/ltx-2.3/image-to-video",
                arguments={
                    "image_url": fake_uploaded_image,
                    "prompt": "Animate this landscape with gentle wind",
                    "duration": 6,
                    "resolution": "1080p",
                    "aspect_ratio": "auto",
                    "fps": 25,
                    "generate_audio": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_end_image(self):
        """Test generation with end image for transitions."""
        image = _make_image_artifact()
        end_image = _make_image_artifact()
        input_data = Ltx23ImageToVideoInput(
            image=image,
            prompt="Transition between scenes",
            end_image=end_image,
            duration=10,
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image = "https://fal.ai/uploaded/image.png"
        fake_uploaded_end_image = "https://fal.ai/uploaded/end_image.png"

        upload_call_count = 0

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-transition"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "width": 1920,
                        "height": 1080,
                        "duration": 10.0,
                        "fps": 25,
                    },
                }
            )

            async def mock_upload(file_path):
                nonlocal upload_call_count
                upload_call_count += 1
                if upload_call_count <= 1:
                    return fake_uploaded_image
                return fake_uploaded_end_image

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
                duration=10.0,
                fps=25,
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

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Both images should be uploaded
            assert mock_fal_client.upload_file_async.call_count == 2

            call_args = mock_fal_client.submit_async.call_args
            arguments = call_args[1]["arguments"]
            assert "end_image_url" in arguments
            assert arguments["duration"] == 10

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        input_data = Ltx23ImageToVideoInput(
            image=_make_image_artifact(),
            prompt="test",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-error"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})

            async def mock_upload(file_path):
                return "https://fal.ai/uploaded/image.png"

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
    async def test_estimate_cost_6_second(self):
        """Test cost estimation for 6-second video."""
        input_data = Ltx23ImageToVideoInput(
            image=_make_image_artifact(),
            prompt="Test",
            duration=6,
        )
        cost = await self.generator.estimate_cost(input_data)
        assert cost == pytest.approx(0.12)

    @pytest.mark.asyncio
    async def test_estimate_cost_10_second(self):
        """Test cost estimation for 10-second video."""
        input_data = Ltx23ImageToVideoInput(
            image=_make_image_artifact(),
            prompt="Test",
            duration=10,
        )
        cost = await self.generator.estimate_cost(input_data)
        assert cost == pytest.approx(0.20)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Ltx23ImageToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "end_image" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "fps" in schema["properties"]
        assert "generate_audio" in schema["properties"]

        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 5000
