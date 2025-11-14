"""
Tests for FalMinimaxSpeech26HdGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.fal_minimax_speech_26_hd import (
    AudioSetting,
    FalMinimaxSpeech26HdGenerator,
    FalMinimaxSpeech26HdInput,
    NormalizationSetting,
    VoiceSetting,
)


class TestFalMinimaxSpeech26HdInput:
    """Tests for FalMinimaxSpeech26HdInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = FalMinimaxSpeech26HdInput(
            prompt="Hello, this is a test speech.",
            voice_setting=VoiceSetting(
                voice_id="Wise_Woman",
                speed=1.2,
                pitch=2,
                vol=0.9,
            ),
            language_boost="English",
            output_format="url",
        )

        assert input_data.prompt == "Hello, this is a test speech."
        assert input_data.voice_setting.voice_id == "Wise_Woman"
        assert input_data.voice_setting.speed == 1.2
        assert input_data.voice_setting.pitch == 2
        assert input_data.voice_setting.vol == 0.9
        assert input_data.language_boost == "English"
        assert input_data.output_format == "url"

    def test_input_defaults(self):
        """Test default values."""
        input_data = FalMinimaxSpeech26HdInput(
            prompt="Test prompt",
        )

        # Check default voice settings
        assert input_data.voice_setting.voice_id == "Wise_Woman"
        assert input_data.voice_setting.speed == 1.0
        assert input_data.voice_setting.pitch == 0
        assert input_data.voice_setting.vol == 1.0
        assert input_data.voice_setting.english_normalization is False

        # Check default language and format
        assert input_data.language_boost is None
        assert input_data.output_format == "url"

        # Check default audio settings
        assert input_data.audio_setting.format == "mp3"
        assert input_data.audio_setting.sample_rate == 32000
        assert input_data.audio_setting.channel == 1
        assert input_data.audio_setting.bitrate == 128000

        # Check default normalization settings
        assert input_data.normalization_setting.enabled is True
        assert input_data.normalization_setting.target_loudness == -18.0
        assert input_data.normalization_setting.target_range == 8.0
        assert input_data.normalization_setting.target_peak == -0.5

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_prompt_length_validation(self):
        """Test validation for prompt length constraints."""
        # Test empty prompt (below minimum)
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(prompt="")

        # Test prompt exceeding maximum (10,000 characters)
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(prompt="a" * 10001)

        # Test valid maximum length
        input_data = FalMinimaxSpeech26HdInput(prompt="a" * 10000)
        assert len(input_data.prompt) == 10000

    def test_voice_setting_validation(self):
        """Test validation for voice settings."""
        # Test speed out of range
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                voice_setting=VoiceSetting(speed=0.3),  # Below minimum of 0.5
            )

        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                voice_setting=VoiceSetting(speed=2.5),  # Above maximum of 2.0
            )

        # Test vol out of range
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                voice_setting=VoiceSetting(vol=0.005),  # Below minimum of 0.01
            )

        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                voice_setting=VoiceSetting(vol=15.0),  # Above maximum of 10
            )

        # Test pitch out of range
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                voice_setting=VoiceSetting(pitch=-13),  # Below minimum of -12
            )

        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                voice_setting=VoiceSetting(pitch=13),  # Above maximum of 12
            )

    def test_audio_setting_validation(self):
        """Test validation for audio settings."""
        # Test invalid format
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                audio_setting=AudioSetting(format="wav"),  # type: ignore[arg-type]
            )

        # Test invalid sample rate
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                audio_setting=AudioSetting(sample_rate=48000),  # type: ignore[arg-type]
            )

        # Test invalid channel
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                audio_setting=AudioSetting(channel=3),  # type: ignore[arg-type]
            )

        # Test valid audio settings
        input_data = FalMinimaxSpeech26HdInput(
            prompt="Test",
            audio_setting=AudioSetting(
                format="flac", sample_rate=44100, channel=2, bitrate=256000
            ),
        )
        assert input_data.audio_setting.format == "flac"
        assert input_data.audio_setting.sample_rate == 44100
        assert input_data.audio_setting.channel == 2
        assert input_data.audio_setting.bitrate == 256000

    def test_normalization_setting_validation(self):
        """Test validation for normalization settings."""
        # Test target_loudness out of range
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                normalization_setting=NormalizationSetting(
                    target_loudness=-80.0  # Below minimum of -70
                ),
            )

        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                normalization_setting=NormalizationSetting(
                    target_loudness=-5.0  # Above maximum of -10
                ),
            )

        # Test target_range out of range
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                normalization_setting=NormalizationSetting(target_range=-1.0),
            )

        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                normalization_setting=NormalizationSetting(target_range=25.0),
            )

        # Test target_peak out of range
        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                normalization_setting=NormalizationSetting(target_peak=-5.0),
            )

        with pytest.raises(ValidationError):
            FalMinimaxSpeech26HdInput(
                prompt="Test",
                normalization_setting=NormalizationSetting(target_peak=1.0),
            )


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalMinimaxSpeech26HdGenerator:
    """Tests for FalMinimaxSpeech26HdGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalMinimaxSpeech26HdGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-minimax-speech-26-hd"
        assert self.generator.artifact_type == "audio"
        assert "text-to-speech" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == FalMinimaxSpeech26HdInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = FalMinimaxSpeech26HdInput(
                prompt="Test speech generation",
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
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    return AudioArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        format="mp3",
                        duration=0.0,
                        sample_rate=None,
                        channels=None,
                    )

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
        """Test successful generation with audio output."""
        input_data = FalMinimaxSpeech26HdInput(
            prompt="Hello world, this is a test.",
            voice_setting=VoiceSetting(voice_id="Wise_Woman"),
            output_format="url",
        )

        fake_audio_url = "https://storage.googleapis.com/falserverless/audio_output.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            # Mock fal_client module
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
                        "url": fake_audio_url,
                    },
                    "duration_ms": 5000,
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="mp3",
                duration=5.0,
                sample_rate=None,
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

                async def store_image_result(self, **kwargs):
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

            # Verify API calls
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/minimax/speech-2.6-hd",
                arguments={
                    "prompt": "Hello world, this is a test.",
                    "output_format": "url",
                    "voice_setting": {
                        "voice_id": "Wise_Woman",
                        "speed": 1.0,
                        "pitch": 0,
                        "vol": 1.0,
                        "english_normalization": False,
                    },
                    "audio_setting": {
                        "format": "mp3",
                        "sample_rate": 32000,
                        "channel": 1,
                        "bitrate": 128000,
                    },
                    "normalization_setting": {
                        "enabled": True,
                        "target_loudness": -18.0,
                        "target_range": 8.0,
                        "target_peak": -0.5,
                    },
                },
            )

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = FalMinimaxSpeech26HdInput(
            prompt="Test",
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

                async def store_image_result(self, **kwargs):
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

            with pytest.raises(ValueError, match="No audio data returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_missing_audio_url(self):
        """Test generation fails when audio URL is missing."""
        input_data = FalMinimaxSpeech26HdInput(
            prompt="Test",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-999"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={"audio": {}}  # Audio field exists but no URL
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

                async def store_image_result(self, **kwargs):
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

            with pytest.raises(ValueError, match="Audio URL missing"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = FalMinimaxSpeech26HdInput(
            prompt="Test prompt",
        )

        cost = await self.generator.estimate_cost(input_data)

        # HD version is $0.015 per generation
        assert cost == 0.015
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = FalMinimaxSpeech26HdInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "voice_setting" in schema["properties"]
        assert "language_boost" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "audio_setting" in schema["properties"]
        assert "normalization_setting" in schema["properties"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 10000

        # Check output_format is enum
        output_format_prop = schema["properties"]["output_format"]
        assert "enum" in output_format_prop or "anyOf" in output_format_prop
