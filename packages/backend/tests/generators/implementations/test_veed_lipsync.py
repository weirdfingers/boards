"""
Tests for FalVeedLipsyncGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from boards.generators.artifacts import AudioArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.veed_lipsync import (
    FalVeedLipsyncGenerator,
    VeedLipsyncInput,
)


class TestVeedLipsyncInput:
    """Tests for VeedLipsyncInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=10.0,
            fps=30.0,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = VeedLipsyncInput(
            video_url=video_artifact,
            audio_url=audio_artifact,
        )

        assert input_data.video_url == video_artifact
        assert input_data.audio_url == audio_artifact


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalVeedLipsyncGenerator:
    """Tests for FalVeedLipsyncGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalVeedLipsyncGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "veed-lipsync"
        assert self.generator.artifact_type == "video"
        assert "lipsync" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == VeedLipsyncInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            video_artifact = VideoArtifact(
                generation_id="gen1",
                storage_url="https://example.com/video.mp4",
                format="mp4",
                width=1920,
                height=1080,
                duration=None,
                fps=None,
            )
            audio_artifact = AudioArtifact(
                generation_id="gen2",
                storage_url="https://example.com/audio.wav",
                format="wav",
                duration=None,
                sample_rate=None,
                channels=None,
            )

            input_data = VeedLipsyncInput(
                video_url=video_artifact,
                audio_url=audio_artifact,
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

                async def store_video_result(self, *args, **kwargs):
                    return VideoArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        width=1,
                        height=1,
                        format="mp4",
                        duration=None,
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
        """Test successful generation with basic parameters."""
        video_artifact = VideoArtifact(
            generation_id="gen_input_video",
            storage_url="https://example.com/input-video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=15.0,
            fps=30.0,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=12.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = VeedLipsyncInput(
            video_url=video_artifact,
            audio_url=audio_artifact,
        )

        fake_output_url = "https://v3.fal.media/files/penguin/output.mp4"
        fake_uploaded_video_url = "https://v3.fal.media/files/uploaded-video.mp4"
        fake_uploaded_audio_url = "https://v3.fal.media/files/uploaded-audio.wav"

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
                        "file_size": 4404019,
                    }
                }
            )

            # Track upload calls to return different URLs for video and audio
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_video_url if upload_call_count == 0 else fake_uploaded_audio_url
                upload_call_count += 1
                return url

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_video_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1920,
                height=1080,
                format="mp4",
                duration=12.0,
                fps=30.0,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    # Return different fake paths for video and audio
                    if isinstance(artifact, VideoArtifact):
                        return "/tmp/fake_video.mp4"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio.wav"
                    return "/tmp/fake_file"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_video_artifact

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
            assert result.outputs[0] == mock_video_artifact

            # Verify file uploads were called for both video and audio
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API calls with uploaded URLs
            mock_fal_client.submit_async.assert_called_once_with(
                "veed/lipsync",
                arguments={
                    "video_url": fake_uploaded_video_url,
                    "audio_url": fake_uploaded_audio_url,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        video_artifact = VideoArtifact(
            generation_id="gen_input_video",
            storage_url="https://example.com/input-video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=None,
            fps=None,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = VeedLipsyncInput(
            video_url=video_artifact,
            audio_url=audio_artifact,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video in response

            fake_uploaded_video_url = "https://v3.fal.media/files/uploaded-video.mp4"
            fake_uploaded_audio_url = "https://v3.fal.media/files/uploaded-audio.wav"

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_video_url if upload_call_count == 0 else fake_uploaded_audio_url
                upload_call_count += 1
                return url

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
                    if isinstance(artifact, VideoArtifact):
                        return "/tmp/fake_video.mp4"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio.wav"
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
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=None,
            fps=None,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = VeedLipsyncInput(
            video_url=video_artifact,
            audio_url=audio_artifact,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Fixed cost
        assert cost == 0.05
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = VeedLipsyncInput.model_json_schema()

        assert schema["type"] == "object"
        assert "video_url" in schema["properties"]
        assert "audio_url" in schema["properties"]

        # Check that video_url and audio_url are required
        assert "video_url" in schema["required"]
        assert "audio_url" in schema["required"]
