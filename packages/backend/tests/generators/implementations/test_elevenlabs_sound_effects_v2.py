"""
Tests for FalElevenlabsSoundEffectsV2Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.elevenlabs_sound_effects_v2 import (
    ElevenlabsSoundEffectsV2Input,
    FalElevenlabsSoundEffectsV2Generator,
)


class TestElevenlabsSoundEffectsV2Input:
    """Tests for ElevenlabsSoundEffectsV2Input schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Spacious braam suitable for high-impact movie trailer moments",
            duration_seconds=5.0,
            prompt_influence=0.5,
            output_format="mp3_44100_128",
            loop=False,
        )

        assert input_data.text == "Spacious braam suitable for high-impact movie trailer moments"
        assert input_data.duration_seconds == 5.0
        assert input_data.prompt_influence == 0.5
        assert input_data.output_format == "mp3_44100_128"
        assert input_data.loop is False

    def test_input_defaults(self):
        """Test default values."""
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test sound effect",
        )

        # Check defaults
        assert input_data.duration_seconds is None
        assert input_data.prompt_influence == 0.3
        assert input_data.output_format == "mp3_44100_128"
        assert input_data.loop is False

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            ElevenlabsSoundEffectsV2Input(
                text="Test",
                output_format="invalid_format",  # type: ignore[arg-type]
            )

    def test_valid_output_formats(self):
        """Test valid output format options."""
        # Test MP3 formats
        for format_option in ["mp3_22050_32", "mp3_44100_128", "mp3_44100_192"]:
            input_data = ElevenlabsSoundEffectsV2Input(
                text="Test",
                output_format=format_option,  # type: ignore[arg-type]
            )
            assert input_data.output_format == format_option

        # Test PCM formats
        for format_option in ["pcm_8000", "pcm_44100", "pcm_48000"]:
            input_data = ElevenlabsSoundEffectsV2Input(
                text="Test",
                output_format=format_option,  # type: ignore[arg-type]
            )
            assert input_data.output_format == format_option

        # Test Opus formats
        for format_option in ["opus_48000_32", "opus_48000_128", "opus_48000_192"]:
            input_data = ElevenlabsSoundEffectsV2Input(
                text="Test",
                output_format=format_option,  # type: ignore[arg-type]
            )
            assert input_data.output_format == format_option

    def test_duration_validation(self):
        """Test validation for duration constraints."""
        # Test duration below minimum (0.5)
        with pytest.raises(ValidationError):
            ElevenlabsSoundEffectsV2Input(
                text="Test",
                duration_seconds=0.4,
            )

        # Test duration above maximum (22.0)
        with pytest.raises(ValidationError):
            ElevenlabsSoundEffectsV2Input(
                text="Test",
                duration_seconds=23.0,
            )

        # Test valid minimum
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test",
            duration_seconds=0.5,
        )
        assert input_data.duration_seconds == 0.5

        # Test valid maximum
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test",
            duration_seconds=22.0,
        )
        assert input_data.duration_seconds == 22.0

        # Test None (auto-determine)
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test",
            duration_seconds=None,
        )
        assert input_data.duration_seconds is None

    def test_prompt_influence_validation(self):
        """Test validation for prompt influence constraints."""
        # Test below minimum (0.0)
        with pytest.raises(ValidationError):
            ElevenlabsSoundEffectsV2Input(
                text="Test",
                prompt_influence=-0.1,
            )

        # Test above maximum (1.0)
        with pytest.raises(ValidationError):
            ElevenlabsSoundEffectsV2Input(
                text="Test",
                prompt_influence=1.1,
            )

        # Test valid minimum
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test",
            prompt_influence=0.0,
        )
        assert input_data.prompt_influence == 0.0

        # Test valid maximum
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test",
            prompt_influence=1.0,
        )
        assert input_data.prompt_influence == 1.0

    def test_loop_option(self):
        """Test loop configuration."""
        # Test loop enabled
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test looping sound",
            loop=True,
        )
        assert input_data.loop is True

        # Test loop disabled (default)
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test non-looping sound",
        )
        assert input_data.loop is False


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalElevenlabsSoundEffectsV2Generator:
    """Tests for FalElevenlabsSoundEffectsV2Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalElevenlabsSoundEffectsV2Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-elevenlabs-sound-effects-v2"
        assert self.generator.artifact_type == "audio"
        assert "sound effects" in self.generator.description.lower()
        assert "ElevenLabs" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == ElevenlabsSoundEffectsV2Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = ElevenlabsSoundEffectsV2Input(
                text="Test sound effect",
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
        input_data = ElevenlabsSoundEffectsV2Input(
            text="A gentle wind chime tinkling in a soft breeze",
            duration_seconds=3.5,
            prompt_influence=0.4,
            output_format="mp3_44100_128",
            loop=False,
        )

        fake_audio_url = "https://v3.fal.media/files/lion/WgnO-jy6WduosuG_Ibobx_sound_effect.mp3"

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
                        "content_type": "audio/mpeg",
                        "file_name": "sound_effect.mp3",
                        "file_size": 123456,
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
                storage_url=fake_audio_url,
                format="mp3",
                duration=0.0,
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
                "fal-ai/elevenlabs/sound-effects/v2",
                arguments={
                    "text": "A gentle wind chime tinkling in a soft breeze",
                    "prompt_influence": 0.4,
                    "output_format": "mp3_44100_128",
                    "loop": False,
                    "duration_seconds": 3.5,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_without_duration(self):
        """Test successful generation without specifying duration."""
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Thunder sound",
        )

        fake_audio_url = "https://v3.fal.media/files/test/audio.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_audio_url,
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="mp3",
                duration=0.0,
                sample_rate=None,
                channels=None,
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

            # Verify duration_seconds was NOT included in API call
            call_args = mock_fal_client.submit_async.call_args[1]["arguments"]
            assert "duration_seconds" not in call_args
            assert call_args["text"] == "Thunder sound"

    @pytest.mark.asyncio
    async def test_generate_with_opus_format(self):
        """Test generation with Opus output format."""
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Bell ringing",
            output_format="opus_48000_128",
        )

        fake_audio_url = "https://v3.fal.media/files/test/audio.opus"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-opus"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_audio_url,
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="opus",
                duration=0.0,
                sample_rate=None,
                channels=None,
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

                async def store_audio_result(self, **kwargs):
                    # Verify format is extracted correctly
                    assert kwargs["format"] == "opus"
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
            assert result.outputs[0].format == "opus"

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test",
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
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test",
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
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Test sound effect",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Fixed cost per generation
        assert cost == 0.055
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_with_long_duration(self):
        """Test cost estimation with longer duration (should be same)."""
        input_data = ElevenlabsSoundEffectsV2Input(
            text="Long sound effect",
            duration_seconds=22.0,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Cost is fixed regardless of duration
        assert cost == 0.055
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = ElevenlabsSoundEffectsV2Input.model_json_schema()

        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "duration_seconds" in schema["properties"]
        assert "prompt_influence" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "loop" in schema["properties"]

        # Check text is required
        assert "text" in schema["required"]

        # Check duration constraints
        duration_prop = schema["properties"]["duration_seconds"]
        # Handle both direct constraints and anyOf structure
        if "anyOf" in duration_prop:
            number_schema = next(s for s in duration_prop["anyOf"] if s.get("type") == "number")
            assert number_schema["minimum"] == 0.5
            assert number_schema["maximum"] == 22.0
        else:
            assert duration_prop["minimum"] == 0.5
            assert duration_prop["maximum"] == 22.0

        # Check prompt_influence constraints
        influence_prop = schema["properties"]["prompt_influence"]
        assert influence_prop["minimum"] == 0.0
        assert influence_prop["maximum"] == 1.0

        # Check output_format is enum
        output_format_prop = schema["properties"]["output_format"]
        assert "enum" in output_format_prop or "anyOf" in output_format_prop
