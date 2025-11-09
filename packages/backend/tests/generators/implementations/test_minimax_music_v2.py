"""
Tests for FalMinimaxMusicV2Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.minimax_music_v2 import (
    AudioSetting,
    FalMinimaxMusicV2Generator,
    MinimaxMusicV2Input,
)


class TestAudioSetting:
    """Tests for AudioSetting schema."""

    def test_valid_settings(self):
        """Test valid audio settings creation."""
        settings = AudioSetting(
            format="mp3",
            sample_rate=44100,
            bitrate=256000,
        )

        assert settings.format == "mp3"
        assert settings.sample_rate == 44100
        assert settings.bitrate == 256000

    def test_default_values(self):
        """Test default values."""
        settings = AudioSetting()

        assert settings.format == "mp3"
        assert settings.sample_rate == 44100
        assert settings.bitrate == 256000

    def test_invalid_format(self):
        """Test validation fails for invalid format."""
        with pytest.raises(ValidationError):
            AudioSetting(format="wav")  # type: ignore[arg-type]

    def test_invalid_sample_rate(self):
        """Test validation fails for invalid sample rate."""
        with pytest.raises(ValidationError):
            AudioSetting(sample_rate=48000)  # type: ignore[arg-type]

    def test_invalid_bitrate(self):
        """Test validation fails for invalid bitrate."""
        with pytest.raises(ValidationError):
            AudioSetting(bitrate=320000)  # type: ignore[arg-type]

    def test_all_format_options(self):
        """Test all valid format options."""
        valid_formats = ["mp3", "pcm", "flac"]

        for fmt in valid_formats:
            settings = AudioSetting(format=fmt)  # type: ignore[arg-type]
            assert settings.format == fmt

    def test_all_sample_rate_options(self):
        """Test all valid sample rate options."""
        valid_rates = [8000, 16000, 22050, 24000, 32000, 44100]

        for rate in valid_rates:
            settings = AudioSetting(sample_rate=rate)  # type: ignore[arg-type]
            assert settings.sample_rate == rate

    def test_all_bitrate_options(self):
        """Test all valid bitrate options."""
        valid_bitrates = [32000, 64000, 128000, 256000]

        for bitrate in valid_bitrates:
            settings = AudioSetting(bitrate=bitrate)  # type: ignore[arg-type]
            assert settings.bitrate == bitrate


class TestMinimaxMusicV2Input:
    """Tests for MinimaxMusicV2Input schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = MinimaxMusicV2Input(
            prompt="Upbeat pop music with electronic beats",
            lyrics_prompt="[Verse]\nDancing in the moonlight\n[Chorus]\nFeel the rhythm tonight",
        )

        assert input_data.prompt == "Upbeat pop music with electronic beats"
        assert "[Verse]" in input_data.lyrics_prompt
        assert input_data.audio_setting is None

    def test_input_with_audio_settings(self):
        """Test input with custom audio settings."""
        audio_setting = AudioSetting(
            format="flac",
            sample_rate=32000,
            bitrate=128000,
        )

        input_data = MinimaxMusicV2Input(
            prompt="Relaxing ambient music",
            lyrics_prompt="[Intro]\nCalm and peaceful",
            audio_setting=audio_setting,
        )

        assert input_data.audio_setting is not None
        assert input_data.audio_setting.format == "flac"
        assert input_data.audio_setting.sample_rate == 32000
        assert input_data.audio_setting.bitrate == 128000

    def test_input_defaults(self):
        """Test default values."""
        input_data = MinimaxMusicV2Input(
            prompt="Test music",
            lyrics_prompt="Test lyrics for music generation",
        )

        assert input_data.audio_setting is None

    def test_prompt_min_length_validation(self):
        """Test validation fails for prompt below minimum length."""
        with pytest.raises(ValidationError):
            MinimaxMusicV2Input(
                prompt="short",  # Less than 10 characters
                lyrics_prompt="Valid lyrics here for the test",
            )

    def test_prompt_max_length_validation(self):
        """Test validation fails for prompt above maximum length."""
        long_prompt = "x" * 301  # More than 300 characters
        with pytest.raises(ValidationError):
            MinimaxMusicV2Input(
                prompt=long_prompt,
                lyrics_prompt="Valid lyrics here for the test",
            )

    def test_lyrics_min_length_validation(self):
        """Test validation fails for lyrics below minimum length."""
        with pytest.raises(ValidationError):
            MinimaxMusicV2Input(
                prompt="Valid music prompt here",
                lyrics_prompt="short",  # Less than 10 characters
            )

    def test_lyrics_max_length_validation(self):
        """Test validation fails for lyrics above maximum length."""
        long_lyrics = "x" * 3001  # More than 3000 characters
        with pytest.raises(ValidationError):
            MinimaxMusicV2Input(
                prompt="Valid music prompt here",
                lyrics_prompt=long_lyrics,
            )

    def test_prompt_exactly_min_length(self):
        """Test prompt with exactly minimum length (10 chars)."""
        input_data = MinimaxMusicV2Input(
            prompt="1234567890",  # Exactly 10 characters
            lyrics_prompt="Valid lyrics here for the test",
        )
        assert len(input_data.prompt) == 10

    def test_prompt_exactly_max_length(self):
        """Test prompt with exactly maximum length (300 chars)."""
        prompt = "x" * 300  # Exactly 300 characters
        input_data = MinimaxMusicV2Input(
            prompt=prompt,
            lyrics_prompt="Valid lyrics here for the test",
        )
        assert len(input_data.prompt) == 300


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalMinimaxMusicV2Generator:
    """Tests for FalMinimaxMusicV2Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalMinimaxMusicV2Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-minimax-music-v2"
        assert self.generator.artifact_type == "audio"
        assert "music" in self.generator.description.lower()
        assert "MiniMax" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == MinimaxMusicV2Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = MinimaxMusicV2Input(
                prompt="Test music prompt",
                lyrics_prompt="Test lyrics for music generation",
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

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
        """Test successful generation."""
        input_data = MinimaxMusicV2Input(
            prompt="Upbeat pop music with electronic beats and catchy melody",
            lyrics_prompt=(
                "[Verse]\nDancing in the moonlight\nFeeling so alive\n"
                "[Chorus]\nWe're gonna party tonight"
            ),
            audio_setting=AudioSetting(
                format="mp3",
                sample_rate=44100,
                bitrate=256000,
            ),
        )

        fake_output_url = "https://v3.fal.media/files/lion/b3-wJ5bbmVo8S-KPqDBMK_output.mp3"

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
                    "audio": {
                        "url": fake_output_url,
                        "content_type": "audio/mpeg",
                        "file_size": 2457600,
                        "file_name": "output.mp3",
                    }
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                format="mp3",
                sample_rate=44100,
                duration=None,
                channels=None,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, **kwargs):
                    return mock_artifact

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

            # Verify API call
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/minimax-music/v2",
                arguments={
                    "prompt": "Upbeat pop music with electronic beats and catchy melody",
                    "lyrics_prompt": (
                        "[Verse]\nDancing in the moonlight\nFeeling so alive\n"
                        "[Chorus]\nWe're gonna party tonight"
                    ),
                    "audio_setting": {
                        "format": "mp3",
                        "sample_rate": 44100,
                        "bitrate": 256000,
                    },
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_without_audio_settings(self):
        """Test successful generation without custom audio settings."""
        input_data = MinimaxMusicV2Input(
            prompt="Relaxing ambient music for meditation and focus",
            lyrics_prompt="[Intro]\nCalm and peaceful\nRelax your mind",
        )

        fake_output_url = "https://v3.fal.media/files/lion/test-output.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_output_url,
                        "content_type": "audio/mpeg",
                        "file_size": 1024000,
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                format="mp3",
                sample_rate=44100,
                duration=None,
                channels=None,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, **kwargs):
                    return mock_artifact

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

            # Verify API call doesn't include audio_setting
            call_args = mock_fal_client.submit_async.call_args
            assert "audio_setting" not in call_args[1]["arguments"]

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = MinimaxMusicV2Input(
            prompt="Test music prompt",
            lyrics_prompt="Test lyrics for music generation",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No audio field

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="No audio returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_audio_missing_url(self):
        """Test generation fails when audio object is missing URL."""
        input_data = MinimaxMusicV2Input(
            prompt="Test music prompt",
            lyrics_prompt="Test lyrics for music generation",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-999"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "content_type": "audio/mpeg",
                        "file_size": 1024000,
                        # Missing 'url' field
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="Audio missing URL"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = MinimaxMusicV2Input(
            prompt="Test music prompt",
            lyrics_prompt="Test lyrics for music generation",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Cost is $0.08 per generation
        assert cost == 0.08
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = MinimaxMusicV2Input.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "lyrics_prompt" in schema["properties"]
        assert "audio_setting" in schema["properties"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 10
        assert prompt_prop["maxLength"] == 300

        # Check lyrics_prompt constraints
        lyrics_prop = schema["properties"]["lyrics_prompt"]
        assert lyrics_prop["minLength"] == 10
        assert lyrics_prop["maxLength"] == 3000

        # Check required fields
        assert "prompt" in schema["required"]
        assert "lyrics_prompt" in schema["required"]
