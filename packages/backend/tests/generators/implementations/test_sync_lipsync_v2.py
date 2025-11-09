"""
Tests for FalSyncLipsyncV2Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.sync_lipsync_v2 import (
    FalSyncLipsyncV2Generator,
    SyncLipsyncV2Input,
)


class TestSyncLipsyncV2Input:
    """Tests for SyncLipsyncV2Input schema."""

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

        input_data = SyncLipsyncV2Input(
            video=video_artifact,
            audio=audio_artifact,
            model="lipsync-2-pro",
            sync_mode="loop",
        )

        assert input_data.video == video_artifact
        assert input_data.audio == audio_artifact
        assert input_data.model == "lipsync-2-pro"
        assert input_data.sync_mode == "loop"

    def test_input_defaults(self):
        """Test default values."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
        )

        input_data = SyncLipsyncV2Input(
            video=video_artifact,
            audio=audio_artifact,
        )

        assert input_data.model == "lipsync-2"
        assert input_data.sync_mode == "cut_off"

    def test_invalid_model(self):
        """Test validation fails for invalid model."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
        )

        with pytest.raises(ValidationError):
            SyncLipsyncV2Input(
                video=video_artifact,
                audio=audio_artifact,
                model="invalid-model",  # type: ignore[arg-type]
            )

    def test_invalid_sync_mode(self):
        """Test validation fails for invalid sync mode."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
        )

        with pytest.raises(ValidationError):
            SyncLipsyncV2Input(
                video=video_artifact,
                audio=audio_artifact,
                sync_mode="invalid-mode",  # type: ignore[arg-type]
            )

    def test_model_options(self):
        """Test all valid model options."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
        )

        valid_models = ["lipsync-2", "lipsync-2-pro"]

        for model in valid_models:
            input_data = SyncLipsyncV2Input(
                video=video_artifact,
                audio=audio_artifact,
                model=model,  # type: ignore[arg-type]
            )
            assert input_data.model == model

    def test_sync_mode_options(self):
        """Test all valid sync mode options."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
        )

        valid_sync_modes = ["cut_off", "loop", "bounce", "silence", "remap"]

        for sync_mode in valid_sync_modes:
            input_data = SyncLipsyncV2Input(
                video=video_artifact,
                audio=audio_artifact,
                sync_mode=sync_mode,  # type: ignore[arg-type]
            )
            assert input_data.sync_mode == sync_mode


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalSyncLipsyncV2Generator:
    """Tests for FalSyncLipsyncV2Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalSyncLipsyncV2Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-sync-lipsync-v2"
        assert self.generator.artifact_type == "video"
        assert "lip-sync" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == SyncLipsyncV2Input

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
            )
            audio_artifact = AudioArtifact(
                generation_id="gen2",
                storage_url="https://example.com/audio.wav",
                format="wav",
            )

            input_data = SyncLipsyncV2Input(
                video=video_artifact,
                audio=audio_artifact,
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

        input_data = SyncLipsyncV2Input(
            video=video_artifact,
            audio=audio_artifact,
            model="lipsync-2",
            sync_mode="cut_off",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_video_url = "https://fal.media/files/uploaded-video.mp4"
        fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio.wav"

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
                url = (
                    fake_uploaded_video_url
                    if upload_call_count == 0
                    else fake_uploaded_audio_url
                )
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
                "fal-ai/sync-lipsync/v2",
                arguments={
                    "video_url": fake_uploaded_video_url,
                    "audio_url": fake_uploaded_audio_url,
                    "model": "lipsync-2",
                    "sync_mode": "cut_off",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_pro_model(self):
        """Test successful generation with pro model and different sync mode."""
        video_artifact = VideoArtifact(
            generation_id="gen_input_video",
            storage_url="https://example.com/input-video.mp4",
            format="mp4",
            width=1280,
            height=720,
            duration=20.0,
            fps=24.0,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.mp3",
            format="mp3",
            duration=25.0,
            sample_rate=48000,
            channels=1,
        )

        input_data = SyncLipsyncV2Input(
            video=video_artifact,
            audio=audio_artifact,
            model="lipsync-2-pro",
            sync_mode="loop",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output-pro.mp4"
        fake_uploaded_video_url = "https://fal.media/files/uploaded-video-pro.mp4"
        fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio-pro.mp3"

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
                        "file_name": "output-pro.mp4",
                        "file_size": 8808038,
                    }
                }
            )

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = (
                    fake_uploaded_video_url
                    if upload_call_count == 0
                    else fake_uploaded_audio_url
                )
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_video_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                format="mp4",
                duration=25.0,
                fps=24.0,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    if isinstance(artifact, VideoArtifact):
                        return "/tmp/fake_video_pro.mp4"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio_pro.mp3"
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

            # Verify API call used pro model and loop sync mode
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["model"] == "lipsync-2-pro"
            assert call_args[1]["arguments"]["sync_mode"] == "loop"

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        video_artifact = VideoArtifact(
            generation_id="gen_input_video",
            storage_url="https://example.com/input-video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
        )

        input_data = SyncLipsyncV2Input(
            video=video_artifact,
            audio=audio_artifact,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video in response

            fake_uploaded_video_url = "https://fal.media/files/uploaded-video.mp4"
            fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio.wav"

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = (
                    fake_uploaded_video_url
                    if upload_call_count == 0
                    else fake_uploaded_audio_url
                )
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
    async def test_estimate_cost_base_model(self):
        """Test cost estimation for base model."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
        )

        input_data = SyncLipsyncV2Input(
            video=video_artifact,
            audio=audio_artifact,
            model="lipsync-2",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost (0.05)
        assert cost == 0.05
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_pro_model(self):
        """Test cost estimation for pro model."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
        )

        input_data = SyncLipsyncV2Input(
            video=video_artifact,
            audio=audio_artifact,
            model="lipsync-2-pro",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost * 1.67 (0.05 * 1.67 = 0.0835)
        assert cost == pytest.approx(0.0835, rel=0.001)
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = SyncLipsyncV2Input.model_json_schema()

        assert schema["type"] == "object"
        assert "video" in schema["properties"]
        assert "audio" in schema["properties"]
        assert "model" in schema["properties"]
        assert "sync_mode" in schema["properties"]

        # Check that video and audio are required
        assert "video" in schema["required"]
        assert "audio" in schema["required"]

        # Check model enum values
        model_prop = schema["properties"]["model"]
        assert "enum" in model_prop
        assert "lipsync-2" in model_prop["enum"]
        assert "lipsync-2-pro" in model_prop["enum"]

        # Check sync_mode enum values
        sync_mode_prop = schema["properties"]["sync_mode"]
        assert "enum" in sync_mode_prop
        assert "cut_off" in sync_mode_prop["enum"]
        assert "loop" in sync_mode_prop["enum"]
