"""
Tests for FalPixverseLipsyncGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.fal_pixverse_lipsync import (
    FalPixverseLipsyncGenerator,
    PixverseLipsyncInput,
)


class TestPixverseLipsyncInput:
    """Tests for PixverseLipsyncInput schema."""

    def test_valid_input_with_audio(self):
        """Test valid input creation with audio."""
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

        input_data = PixverseLipsyncInput(
            video_url=video_artifact,
            audio_url=audio_artifact,
            voice_id="Emily",
        )

        assert input_data.video_url == video_artifact
        assert input_data.audio_url == audio_artifact
        assert input_data.text is None
        assert input_data.voice_id == "Emily"

    def test_valid_input_with_text(self):
        """Test valid input creation with text for TTS."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=10.0,
            fps=30.0,
        )

        input_data = PixverseLipsyncInput(
            video_url=video_artifact, text="Hello, this is a test message.", voice_id="James"
        )

        assert input_data.video_url == video_artifact
        assert input_data.audio_url is None
        assert input_data.text == "Hello, this is a test message."
        assert input_data.voice_id == "James"

    def test_input_defaults(self):
        """Test default values."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=None,
            fps=None,
        )

        input_data = PixverseLipsyncInput(video_url=video_artifact, text="Test")

        assert input_data.audio_url is None
        assert input_data.voice_id == "Auto"

    def test_invalid_voice_id(self):
        """Test validation fails for invalid voice_id."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=None,
            fps=None,
        )

        with pytest.raises(ValidationError):
            PixverseLipsyncInput(
                video_url=video_artifact,
                text="Test",
                voice_id="InvalidVoice",  # type: ignore[arg-type]
            )

    def test_voice_id_options(self):
        """Test all valid voice_id options."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=None,
            fps=None,
        )

        valid_voices = [
            "Emily",
            "James",
            "Isabella",
            "Liam",
            "Chloe",
            "Adrian",
            "Harper",
            "Ava",
            "Sophia",
            "Julia",
            "Mason",
            "Jack",
            "Oliver",
            "Ethan",
            "Auto",
        ]

        for voice in valid_voices:
            input_data = PixverseLipsyncInput(
                video_url=video_artifact,
                text="Test",
                voice_id=voice,  # type: ignore[arg-type]
            )
            assert input_data.voice_id == voice


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalPixverseLipsyncGenerator:
    """Tests for FalPixverseLipsyncGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalPixverseLipsyncGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-pixverse-lipsync"
        assert self.generator.artifact_type == "video"
        assert "lip-sync" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == PixverseLipsyncInput

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

            input_data = PixverseLipsyncInput(video_url=video_artifact, text="Test")

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
    async def test_generate_missing_audio_and_text(self):
        """Test generation fails when both audio and text are missing."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=10.0,
            fps=30.0,
        )

        input_data = PixverseLipsyncInput(video_url=video_artifact)

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            async def mock_upload(file_path):
                return "https://fal.media/files/uploaded-video.mp4"

            mock_fal_client = ModuleType("fal_client")
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

            with pytest.raises(ValueError, match="Either audio_url or text must be provided"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful_with_audio(self):
        """Test successful generation with audio input."""
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

        input_data = PixverseLipsyncInput(
            video_url=video_artifact, audio_url=audio_artifact, voice_id="Emily"
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
                "fal-ai/pixverse/lipsync",
                arguments={
                    "video_url": fake_uploaded_video_url,
                    "audio_url": fake_uploaded_audio_url,
                    "voice_id": "Emily",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_with_text_tts(self):
        """Test successful generation with text (TTS)."""
        video_artifact = VideoArtifact(
            generation_id="gen_input_video",
            storage_url="https://example.com/input-video.mp4",
            format="mp4",
            width=1280,
            height=720,
            duration=10.0,
            fps=24.0,
        )

        input_data = PixverseLipsyncInput(
            video_url=video_artifact, text="Hello, this is a test message.", voice_id="James"
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output-tts.mp4"
        fake_uploaded_video_url = "https://fal.media/files/uploaded-video-tts.mp4"

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
                        "file_name": "output-tts.mp4",
                        "file_size": 3303014,
                    }
                }
            )

            async def mock_upload(file_path):
                return fake_uploaded_video_url

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
                duration=10.0,
                fps=24.0,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    if isinstance(artifact, VideoArtifact):
                        return "/tmp/fake_video_tts.mp4"
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

            # Verify only video upload was called (no audio since using TTS)
            assert mock_fal_client.upload_file_async.call_count == 1

            # Verify API call used text instead of audio_url
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["video_url"] == fake_uploaded_video_url
            assert call_args[1]["arguments"]["text"] == "Hello, this is a test message."
            assert call_args[1]["arguments"]["voice_id"] == "James"
            assert "audio_url" not in call_args[1]["arguments"]

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

        input_data = PixverseLipsyncInput(video_url=video_artifact, text="Test")

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video in response

            fake_uploaded_video_url = "https://fal.media/files/uploaded-video.mp4"

            async def mock_upload(file_path):
                return fake_uploaded_video_url

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
    async def test_estimate_cost_with_audio(self):
        """Test cost estimation with audio input."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=10.0,  # 10 seconds
            fps=None,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=None,
            channels=None,
        )

        input_data = PixverseLipsyncInput(video_url=video_artifact, audio_url=audio_artifact)

        cost = await self.generator.estimate_cost(input_data)

        # 10 seconds * $0.04/second = $0.40
        assert cost == pytest.approx(0.40, rel=0.001)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_with_text_tts(self):
        """Test cost estimation with text (TTS)."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,  # 5 seconds
            fps=None,
        )

        # 150 characters for TTS
        text = "A" * 150

        input_data = PixverseLipsyncInput(video_url=video_artifact, text=text)

        cost = await self.generator.estimate_cost(input_data)

        # Video cost: 5 seconds * $0.04/second = $0.20
        # TTS cost: 150 characters * $0.24/100 chars = $0.36
        # Total: $0.56
        expected_cost = 0.20 + 0.36
        assert cost == pytest.approx(expected_cost, rel=0.001)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_default_duration(self):
        """Test cost estimation with unknown video duration (uses default)."""
        video_artifact = VideoArtifact(
            generation_id="gen1",
            storage_url="https://example.com/video.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=None,  # Unknown duration
            fps=None,
        )

        input_data = PixverseLipsyncInput(video_url=video_artifact, text="Test")

        cost = await self.generator.estimate_cost(input_data)

        # Default 5 seconds * $0.04/second = $0.20
        # TTS: 4 chars * $0.24/100 = $0.0096
        # Total: ~$0.21
        assert cost > 0.20
        assert cost < 0.30  # Sanity check
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = PixverseLipsyncInput.model_json_schema()

        assert schema["type"] == "object"
        assert "video_url" in schema["properties"]
        assert "audio_url" in schema["properties"]
        assert "text" in schema["properties"]
        assert "voice_id" in schema["properties"]

        # Check that only video_url is required
        assert "video_url" in schema["required"]
        assert "audio_url" not in schema.get("required", [])
        assert "text" not in schema.get("required", [])

        # Check voice_id enum values
        voice_prop = schema["properties"]["voice_id"]
        assert "enum" in voice_prop or "anyOf" in voice_prop

        # Extract enum from anyOf if present (Pydantic may wrap it)
        if "anyOf" in voice_prop:
            enum_values = []
            for item in voice_prop["anyOf"]:
                if "enum" in item:
                    enum_values.extend(item["enum"])
            assert "Emily" in enum_values
            assert "James" in enum_values
            assert "Auto" in enum_values
        else:
            assert "Emily" in voice_prop["enum"]
            assert "James" in voice_prop["enum"]
            assert "Auto" in voice_prop["enum"]
