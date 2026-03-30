"""
Tests for FalGrokImagineVideoExtendVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.grok_imagine_video_extend_video import (
    FalGrokImagineVideoExtendVideoGenerator,
    GrokImagineVideoExtendVideoInput,
)


def _make_video(duration: float = 5.0) -> VideoArtifact:
    return VideoArtifact(
        generation_id="gen_vid",
        storage_url="https://example.com/video.mp4",
        format="mp4",
        width=1280,
        height=720,
        duration=duration,
        fps=30.0,
    )


class TestGrokImagineVideoExtendVideoInput:
    """Tests for GrokImagineVideoExtendVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        video = _make_video()
        inp = GrokImagineVideoExtendVideoInput(
            prompt="The camera pans to reveal a sunset",
            video=video,
            duration=8,
        )
        assert inp.prompt == "The camera pans to reveal a sunset"
        assert inp.video == video
        assert inp.duration == 8

    def test_input_defaults(self):
        """Test default values."""
        inp = GrokImagineVideoExtendVideoInput(
            prompt="Continue the scene",
            video=_make_video(),
        )
        assert inp.duration == 6

    def test_invalid_duration_too_low(self):
        """Test validation fails for duration below minimum."""
        with pytest.raises(ValidationError):
            GrokImagineVideoExtendVideoInput(
                prompt="Test",
                video=_make_video(),
                duration=1,
            )

    def test_invalid_duration_too_high(self):
        """Test validation fails for duration above maximum."""
        with pytest.raises(ValidationError):
            GrokImagineVideoExtendVideoInput(
                prompt="Test",
                video=_make_video(),
                duration=15,
            )

    def test_all_valid_durations(self):
        """Test all valid duration values (2-10)."""
        for d in range(2, 11):
            inp = GrokImagineVideoExtendVideoInput(
                prompt="Test",
                video=_make_video(),
                duration=d,
            )
            assert inp.duration == d

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = GrokImagineVideoExtendVideoInput.model_json_schema()
        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "video" in schema["properties"]
        assert "duration" in schema["properties"]
        assert set(schema["required"]) == {"prompt", "video"}


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalGrokImagineVideoExtendVideoGenerator:
    """Tests for FalGrokImagineVideoExtendVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalGrokImagineVideoExtendVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-grok-imagine-video-extend-video"
        assert self.generator.artifact_type == "video"
        assert "Grok Imagine Video" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == GrokImagineVideoExtendVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            inp = GrokImagineVideoExtendVideoInput(
                prompt="Test",
                video=_make_video(),
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
                await self.generator.generate(inp, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful(self):
        """Test successful generation."""
        video = _make_video(duration=5.0)
        inp = GrokImagineVideoExtendVideoInput(
            prompt="The camera reveals a sunset",
            video=video,
            duration=6,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/extended.mp4"
        fake_uploaded_video = "https://fal.media/files/video.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"
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
                return fake_uploaded_video

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                duration=11,
                format="mp4",
                fps=None,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
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

            result = await self.generator.generate(inp, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify API call
            mock_fal_client.submit_async.assert_called_once_with(
                "xai/grok-imagine-video/extend-video",
                arguments={
                    "prompt": "The camera reveals a sunset",
                    "video_url": fake_uploaded_video,
                    "duration": 6,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        inp = GrokImagineVideoExtendVideoInput(
            prompt="Test",
            video=_make_video(),
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})

            async def mock_upload(file_path):
                return "https://fal.media/files/video.mp4"

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
                    return "/tmp/fake_video.mp4"

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
                await self.generator.generate(inp, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation accounts for input and output duration."""
        video_5s = _make_video(duration=5.0)
        inp = GrokImagineVideoExtendVideoInput(
            prompt="Test",
            video=video_5s,
            duration=6,
        )

        cost = await self.generator.estimate_cost(inp)

        # 0.05 * 6 (output) + 0.01 * 5 (input) = 0.35
        assert abs(cost - 0.35) < 0.001

    @pytest.mark.asyncio
    async def test_estimate_cost_no_input_duration(self):
        """Test cost estimation when input video has no duration."""
        video_no_dur = VideoArtifact(
            generation_id="gen_vid",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1280,
            height=720,
            duration=None,
            fps=None,
        )
        inp = GrokImagineVideoExtendVideoInput(
            prompt="Test",
            video=video_no_dur,
            duration=6,
        )

        cost = await self.generator.estimate_cost(inp)

        # 0.05 * 6 (output) + 0.01 * 0 (no input duration) = 0.30
        assert abs(cost - 0.30) < 0.001
