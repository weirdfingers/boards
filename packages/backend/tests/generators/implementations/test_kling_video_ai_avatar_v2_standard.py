"""
Tests for FalKlingVideoAiAvatarV2StandardGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact, ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.kling_video_ai_avatar_v2_standard import (
    FalKlingVideoAiAvatarV2StandardGenerator,
    KlingVideoAiAvatarV2StandardInput,
)


class TestKlingVideoAiAvatarV2StandardInput:
    """Tests for KlingVideoAiAvatarV2StandardInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = KlingVideoAiAvatarV2StandardInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="A person speaking clearly",
        )

        assert input_data.image == image_artifact
        assert input_data.audio == audio_artifact
        assert input_data.prompt == "A person speaking clearly"

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = KlingVideoAiAvatarV2StandardInput(
            image=image_artifact,
            audio=audio_artifact,
        )

        assert input_data.prompt == "."

    def test_missing_image(self):
        """Test validation fails when image is missing."""
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        with pytest.raises(ValidationError):
            KlingVideoAiAvatarV2StandardInput(
                audio=audio_artifact,  # type: ignore[call-arg]
            )

    def test_missing_audio(self):
        """Test validation fails when audio is missing."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=512,
            height=512,
        )

        with pytest.raises(ValidationError):
            KlingVideoAiAvatarV2StandardInput(
                image=image_artifact,  # type: ignore[call-arg]
            )

    def test_custom_prompt(self):
        """Test custom prompt is accepted."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = KlingVideoAiAvatarV2StandardInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="A cartoon character speaking enthusiastically",
        )

        assert input_data.prompt == "A cartoon character speaking enthusiastically"


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalKlingVideoAiAvatarV2StandardGenerator:
    """Tests for FalKlingVideoAiAvatarV2StandardGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalKlingVideoAiAvatarV2StandardGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-kling-video-ai-avatar-v2-standard"
        assert self.generator.artifact_type == "video"
        assert "avatar" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == KlingVideoAiAvatarV2StandardInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/avatar.jpg",
                format="jpg",
                width=512,
                height=512,
            )
            audio_artifact = AudioArtifact(
                generation_id="gen2",
                storage_url="https://example.com/speech.mp3",
                format="mp3",
                duration=None,
                sample_rate=None,
                channels=None,
            )

            input_data = KlingVideoAiAvatarV2StandardInput(
                image=image_artifact,
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
        """Test successful generation with default parameters."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = KlingVideoAiAvatarV2StandardInput(
            image=image_artifact,
            audio=audio_artifact,
        )

        fake_output_url = "https://v3.fal.media/files/penguin/output.mp4"
        fake_uploaded_image_url = "https://fal.media/files/uploaded-image.jpg"
        fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio.mp3"

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
                    },
                    "duration": 10.0,
                }
            )

            # Track upload calls to return different URLs for image and audio
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
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
                width=512,
                height=512,
                format="mp4",
                duration=10.0,
                fps=None,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    # Return different fake paths for image and audio
                    if isinstance(artifact, ImageArtifact):
                        return "/tmp/fake_image.jpg"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio.mp3"
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

            # Verify file uploads were called for both image and audio
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API calls with uploaded URLs (default prompt is not sent)
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/kling-video/ai-avatar/v2/standard",
                arguments={
                    "image_url": fake_uploaded_image_url,
                    "audio_url": fake_uploaded_audio_url,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_with_prompt(self):
        """Test successful generation with custom prompt."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=1024,
            height=1024,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=15.0,
            sample_rate=48000,
            channels=1,
        )

        input_data = KlingVideoAiAvatarV2StandardInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="A cartoon character speaking with enthusiasm",
        )

        fake_output_url = "https://v3.fal.media/files/penguin/output-with-prompt.mp4"
        fake_uploaded_image_url = "https://fal.media/files/uploaded-image-prompt.jpg"
        fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio-prompt.mp3"

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
                        "file_name": "output-with-prompt.mp4",
                        "file_size": 8808038,
                    },
                    "duration": 15.0,
                }
            )

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_video_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=1024,
                format="mp4",
                duration=15.0,
                fps=None,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    if isinstance(artifact, ImageArtifact):
                        return "/tmp/fake_image_prompt.jpg"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio_prompt.mp3"
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

            # Verify API call includes the custom prompt
            call_args = mock_fal_client.submit_async.call_args
            expected_prompt = "A cartoon character speaking with enthusiasm"
            assert call_args[1]["arguments"]["prompt"] == expected_prompt

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = KlingVideoAiAvatarV2StandardInput(
            image=image_artifact,
            audio=audio_artifact,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video in response

            fake_uploaded_image_url = "https://fal.media/files/uploaded-image.jpg"
            fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio.mp3"

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
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
                    if isinstance(artifact, ImageArtifact):
                        return "/tmp/fake_image.jpg"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio.mp3"
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
            storage_url="https://example.com/avatar.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/speech.mp3",
            format="mp3",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = KlingVideoAiAvatarV2StandardInput(
            image=image_artifact,
            audio=audio_artifact,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Estimated cost (0.10)
        assert cost == 0.10
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = KlingVideoAiAvatarV2StandardInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert "audio" in schema["properties"]
        assert "prompt" in schema["properties"]

        # Check that image and audio are required
        assert "image" in schema["required"]
        assert "audio" in schema["required"]

        # Check prompt has default
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop.get("default") == "."
