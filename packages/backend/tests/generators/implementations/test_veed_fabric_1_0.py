"""
Tests for FalVeedFabric10Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from boards.generators.artifacts import AudioArtifact, ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.veed_fabric_1_0 import (
    FalVeedFabric10Generator,
    VeedFabric10Input,
)


class DummyCtx(GeneratorExecutionContext):
    """Shared test context for all tests."""

    generation_id = "test_gen"
    provider_correlation_id = "corr"
    tenant_id = "test_tenant"
    board_id = "test_board"

    async def resolve_artifact(self, artifact):
        """Resolve artifacts to temporary file paths."""
        if isinstance(artifact, ImageArtifact):
            return "/tmp/fake_image.png"
        elif isinstance(artifact, AudioArtifact):
            return "/tmp/fake_audio.wav"
        return "/tmp/fake_file"

    async def store_image_result(self, **kwargs):
        raise NotImplementedError

    async def store_video_result(self, **kwargs):
        return VideoArtifact(
            generation_id="test_gen",
            storage_url=kwargs.get("storage_url", ""),
            width=kwargs.get("width", 1280),
            height=kwargs.get("height", 720),
            format=kwargs.get("format", "mp4"),
            duration=kwargs.get("duration"),
            fps=kwargs.get("fps"),
        )

    async def store_audio_result(self, *args, **kwargs):
        raise NotImplementedError

    async def store_text_result(self, *args, **kwargs):
        raise NotImplementedError

    async def publish_progress(self, update):
        return None

    async def set_external_job_id(self, external_id: str) -> None:
        return None


class TestVeedFabric10Input:
    """Tests for VeedFabric10Input schema."""

    def test_valid_input(self):
        """Test valid input creation with all fields."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
            resolution="720p",
        )

        assert input_data.image_url == image_artifact
        assert input_data.audio_url == audio_artifact
        assert input_data.resolution == "720p"

    def test_valid_input_480p(self):
        """Test valid input with 480p resolution."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
            resolution="480p",
        )

        assert input_data.resolution == "480p"

    def test_default_resolution(self):
        """Test that resolution defaults to 720p."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
        )

        assert input_data.resolution == "720p"

    def test_invalid_resolution(self):
        """Test that invalid resolution values are rejected."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        with pytest.raises(ValueError):
            VeedFabric10Input(
                image_url=image_artifact,
                audio_url=audio_artifact,
                resolution="1080p",  # type: ignore[arg-type]  # Not a valid option - intentionally testing validation
            )


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalVeedFabric10Generator:
    """Tests for FalVeedFabric10Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalVeedFabric10Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "veed-fabric-1.0"
        assert self.generator.artifact_type == "video"
        assert "fabric" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == VeedFabric10Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=512,
                height=512,
            )
            audio_artifact = AudioArtifact(
                generation_id="gen2",
                storage_url="https://example.com/audio.wav",
                format="wav",
                duration=None,
                sample_rate=None,
                channels=None,
            )

            input_data = VeedFabric10Input(
                image_url=image_artifact,
                audio_url=audio_artifact,
            )

            with pytest.raises(ValueError, match="FAL_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful_720p(self):
        """Test successful generation with 720p resolution."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/input-image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=12.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
            resolution="720p",
        )

        fake_output_url = "https://v3.fal.media/files/penguin/output.mp4"
        fake_uploaded_image_url = "https://v3.fal.media/files/uploaded-image.png"
        fake_uploaded_audio_url = "https://v3.fal.media/files/uploaded-audio.wav"

        # Create mock handler with async iterator for events
        mock_handler = MagicMock()
        mock_handler.request_id = "test-request-123"

        mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

        mock_handler.get = AsyncMock(
            return_value={
                "video": {
                    "url": fake_output_url,
                    "content_type": "video/mp4",
                    "file_name": "output.mp4",
                    "file_size": 4404019,
                }
            }
        )

        # Track upload calls
        upload_call_count = 0

        async def mock_upload(_file_path):
            nonlocal upload_call_count
            url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
            upload_call_count += 1
            return url

        # Create mock fal_client module
        mock_fal_client = ModuleType("fal_client")
        mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
        mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

        # Mock storage result with 720p dimensions
        mock_video_artifact = VideoArtifact(
            generation_id="test_gen",
            storage_url=fake_output_url,
            width=1280,
            height=720,
            format="mp4",
            duration=12.0,
            fps=30.0,
        )

        class CustomCtx(DummyCtx):
            async def store_video_result(self, **kwargs):
                return mock_video_artifact

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            with patch.dict("sys.modules", {"fal_client": mock_fal_client}):
                result = await self.generator.generate(input_data, CustomCtx())

                assert isinstance(result, GeneratorResult)
                assert len(result.outputs) == 1
                assert result.outputs[0] == mock_video_artifact

                # Verify file uploads were called for both image and audio
                assert mock_fal_client.upload_file_async.call_count == 2

                # Verify API calls with uploaded URLs and resolution
                mock_fal_client.submit_async.assert_called_once_with(
                    "veed/fabric-1.0",
                    arguments={
                        "image_url": fake_uploaded_image_url,
                        "audio_url": fake_uploaded_audio_url,
                        "resolution": "720p",
                    },
                )

    @pytest.mark.asyncio
    async def test_generate_successful_480p(self):
        """Test successful generation with 480p resolution."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/input-image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
            resolution="480p",
        )

        fake_output_url = "https://v3.fal.media/files/penguin/output480.mp4"
        fake_uploaded_image_url = "https://v3.fal.media/files/uploaded-image.png"
        fake_uploaded_audio_url = "https://v3.fal.media/files/uploaded-audio.wav"

        mock_handler = MagicMock()
        mock_handler.request_id = "test-request-456"
        mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
        mock_handler.get = AsyncMock(
            return_value={
                "video": {
                    "url": fake_output_url,
                    "content_type": "video/mp4",
                    "file_name": "output.mp4",
                    "file_size": 2000000,
                }
            }
        )

        upload_call_count = 0

        async def mock_upload(_file_path):
            nonlocal upload_call_count
            url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
            upload_call_count += 1
            return url

        mock_fal_client = ModuleType("fal_client")
        mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
        mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

        # Mock storage result with 480p dimensions
        mock_video_artifact = VideoArtifact(
            generation_id="test_gen",
            storage_url=fake_output_url,
            width=854,
            height=480,
            format="mp4",
            duration=10.0,
            fps=30.0,
        )

        class CustomCtx(DummyCtx):
            async def store_video_result(self, **kwargs):
                return mock_video_artifact

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            with patch.dict("sys.modules", {"fal_client": mock_fal_client}):
                result = await self.generator.generate(input_data, CustomCtx())

                assert isinstance(result, GeneratorResult)
                assert len(result.outputs) == 1

                # Verify resolution is passed correctly
                mock_fal_client.submit_async.assert_called_once_with(
                    "veed/fabric-1.0",
                    arguments={
                        "image_url": fake_uploaded_image_url,
                        "audio_url": fake_uploaded_audio_url,
                        "resolution": "480p",
                    },
                )

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/input-image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
        )

        mock_handler = MagicMock()
        mock_handler.request_id = "test-request-789"
        mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
        mock_handler.get = AsyncMock(return_value={})  # No video in response

        fake_uploaded_image_url = "https://v3.fal.media/files/uploaded-image.png"
        fake_uploaded_audio_url = "https://v3.fal.media/files/uploaded-audio.wav"

        upload_call_count = 0

        async def mock_upload(_file_path):
            nonlocal upload_call_count
            url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
            upload_call_count += 1
            return url

        mock_fal_client = ModuleType("fal_client")
        mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
        mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            with patch.dict("sys.modules", {"fal_client": mock_fal_client}):
                with pytest.raises(ValueError, match="No video returned"):
                    await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_video_missing_url(self):
        """Test generation fails when video object has no URL."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/input-image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
        )

        mock_handler = MagicMock()
        mock_handler.request_id = "test-request-999"
        mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
        mock_handler.get = AsyncMock(
            return_value={"video": {"content_type": "video/mp4"}}  # No url field
        )

        fake_uploaded_image_url = "https://v3.fal.media/files/uploaded-image.png"
        fake_uploaded_audio_url = "https://v3.fal.media/files/uploaded-audio.wav"

        upload_call_count = 0

        async def mock_upload(_file_path):
            nonlocal upload_call_count
            url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
            upload_call_count += 1
            return url

        mock_fal_client = ModuleType("fal_client")
        mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
        mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            with patch.dict("sys.modules", {"fal_client": mock_fal_client}):
                with pytest.raises(ValueError, match="Video missing URL"):
                    await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Fixed cost
        assert cost == 0.08
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = VeedFabric10Input.model_json_schema()

        assert schema["type"] == "object"
        assert "image_url" in schema["properties"]
        assert "audio_url" in schema["properties"]
        assert "resolution" in schema["properties"]

        # Check that image_url and audio_url are required
        assert "image_url" in schema["required"]
        assert "audio_url" in schema["required"]
        # resolution has a default, so may not be in required
