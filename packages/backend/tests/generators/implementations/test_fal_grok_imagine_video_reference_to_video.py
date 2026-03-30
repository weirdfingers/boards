"""
Tests for FalGrokImagineVideoReferenceToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.grok_imagine_video_reference_to_video import (
    FalGrokImagineVideoReferenceToVideoGenerator,
    GrokImagineVideoReferenceToVideoInput,
)


def _make_image(gen_id: str = "gen1") -> ImageArtifact:
    return ImageArtifact(
        generation_id=gen_id,
        storage_url=f"https://example.com/{gen_id}.png",
        format="png",
        width=1024,
        height=768,
    )


class TestGrokImagineVideoReferenceToVideoInput:
    """Tests for GrokImagineVideoReferenceToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        images = [_make_image("img1"), _make_image("img2")]
        inp = GrokImagineVideoReferenceToVideoInput(
            prompt="@Image1 walks through a garden",
            reference_images=images,
            duration=6,
            aspect_ratio="16:9",
            resolution="720p",
        )
        assert inp.prompt == "@Image1 walks through a garden"
        assert len(inp.reference_images) == 2
        assert inp.duration == 6
        assert inp.aspect_ratio == "16:9"
        assert inp.resolution == "720p"

    def test_input_defaults(self):
        """Test default values."""
        inp = GrokImagineVideoReferenceToVideoInput(
            prompt="Test prompt",
            reference_images=[_make_image()],
        )
        assert inp.duration == 8
        assert inp.aspect_ratio == "16:9"
        assert inp.resolution == "480p"

    def test_empty_reference_images_rejected(self):
        """Test validation fails with no reference images."""
        with pytest.raises(ValidationError):
            GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=[],
            )

    def test_too_many_reference_images_rejected(self):
        """Test validation fails with more than 7 images."""
        images = [_make_image(f"img{i}") for i in range(8)]
        with pytest.raises(ValidationError):
            GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=images,
            )

    def test_invalid_duration(self):
        """Test validation fails for out-of-range duration."""
        with pytest.raises(ValidationError):
            GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=[_make_image()],
                duration=15,
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=[_make_image()],
                aspect_ratio="2:1",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        with pytest.raises(ValidationError):
            GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=[_make_image()],
                resolution="1080p",  # type: ignore[arg-type]
            )

    def test_all_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        for ratio in ["16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16"]:
            inp = GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=[_make_image()],
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert inp.aspect_ratio == ratio

    def test_all_resolution_options(self):
        """Test all valid resolution options."""
        for res in ["480p", "720p"]:
            inp = GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=[_make_image()],
                resolution=res,  # type: ignore[arg-type]
            )
            assert inp.resolution == res

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = GrokImagineVideoReferenceToVideoInput.model_json_schema()
        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "reference_images" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert set(schema["required"]) == {"prompt", "reference_images"}


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalGrokImagineVideoReferenceToVideoGenerator:
    """Tests for FalGrokImagineVideoReferenceToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalGrokImagineVideoReferenceToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-grok-imagine-video-reference-to-video"
        assert self.generator.artifact_type == "video"
        assert "Grok Imagine Video" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == GrokImagineVideoReferenceToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            inp = GrokImagineVideoReferenceToVideoInput(
                prompt="Test",
                reference_images=[_make_image()],
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
        images = [_make_image("img1"), _make_image("img2")]
        inp = GrokImagineVideoReferenceToVideoInput(
            prompt="@Image1 dances with @Image2",
            reference_images=images,
            duration=6,
            aspect_ratio="16:9",
            resolution="720p",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_urls = [
            "https://fal.media/files/img1.png",
            "https://fal.media/files/img2.png",
        ]

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

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_urls[upload_call_count]
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                duration=6,
                format="mp4",
                fps=None,
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

            result = await self.generator.generate(inp, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify API call
            mock_fal_client.submit_async.assert_called_once_with(
                "xai/grok-imagine-video/reference-to-video",
                arguments={
                    "prompt": "@Image1 dances with @Image2",
                    "reference_image_urls": fake_uploaded_urls,
                    "duration": 6,
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        inp = GrokImagineVideoReferenceToVideoInput(
            prompt="Test",
            reference_images=[_make_image()],
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})

            async def mock_upload(file_path):
                return "https://fal.media/files/image.png"

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
                await self.generator.generate(inp, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation scales with duration."""
        inp_8s = GrokImagineVideoReferenceToVideoInput(
            prompt="Test",
            reference_images=[_make_image()],
            duration=8,
        )
        inp_4s = GrokImagineVideoReferenceToVideoInput(
            prompt="Test",
            reference_images=[_make_image()],
            duration=4,
        )

        cost_8s = await self.generator.estimate_cost(inp_8s)
        cost_4s = await self.generator.estimate_cost(inp_4s)

        assert abs(cost_8s - 0.40) < 0.001
        assert abs(cost_4s - 0.20) < 0.001
        assert cost_8s > cost_4s
