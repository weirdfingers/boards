"""
Tests for FalChatterboxTtsTurboGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.chatterbox_tts_turbo import (
    ChatterboxTtsTurboInput,
    FalChatterboxTtsTurboGenerator,
)


class TestChatterboxTtsTurboInput:
    """Tests for ChatterboxTtsTurboInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = ChatterboxTtsTurboInput(
            text="Hello, this is a test [laugh] with some expression.",
            voice="lucy",
            temperature=0.9,
            seed=42,
        )

        assert input_data.text == "Hello, this is a test [laugh] with some expression."
        assert input_data.voice == "lucy"
        assert input_data.temperature == 0.9
        assert input_data.seed == 42
        assert input_data.audio_url is None

    def test_input_defaults(self):
        """Test default values."""
        input_data = ChatterboxTtsTurboInput(
            text="Test prompt",
        )

        # Check defaults
        assert input_data.voice == "lucy"
        assert input_data.temperature == 0.8
        assert input_data.seed is None
        assert input_data.audio_url is None

    def test_all_preset_voices(self):
        """Test all preset voice options are valid."""
        voices = [
            "aaron",
            "abigail",
            "anaya",
            "andy",
            "archer",
            "brian",
            "chloe",
            "dylan",
            "emmanuel",
            "ethan",
            "evelyn",
            "gavin",
            "gordon",
            "ivan",
            "laura",
            "lucy",
            "madison",
            "marisol",
            "meera",
            "walter",
        ]

        for voice in voices:
            input_data = ChatterboxTtsTurboInput(
                text="Test",
                voice=voice,  # type: ignore[arg-type]
            )
            assert input_data.voice == voice

    def test_invalid_voice(self):
        """Test validation fails for invalid voice."""
        with pytest.raises(ValidationError):
            ChatterboxTtsTurboInput(
                text="Test",
                voice="invalid_voice",  # type: ignore[arg-type]
            )

    def test_empty_text_validation(self):
        """Test validation for empty text."""
        with pytest.raises(ValidationError):
            ChatterboxTtsTurboInput(text="")

    def test_temperature_validation_min(self):
        """Test temperature below minimum."""
        with pytest.raises(ValidationError):
            ChatterboxTtsTurboInput(
                text="Test",
                temperature=0.01,  # Below 0.05 minimum
            )

    def test_temperature_validation_max(self):
        """Test temperature above maximum."""
        with pytest.raises(ValidationError):
            ChatterboxTtsTurboInput(
                text="Test",
                temperature=2.5,  # Above 2.0 maximum
            )

    def test_temperature_at_boundaries(self):
        """Test temperature at boundary values."""
        # Minimum boundary
        input_min = ChatterboxTtsTurboInput(
            text="Test",
            temperature=0.05,
        )
        assert input_min.temperature == 0.05

        # Maximum boundary
        input_max = ChatterboxTtsTurboInput(
            text="Test",
            temperature=2.0,
        )
        assert input_max.temperature == 2.0

    def test_with_audio_artifact(self):
        """Test input with voice cloning audio artifact."""
        audio_artifact = AudioArtifact(
            generation_id="test_audio",
            storage_url="https://example.com/voice_sample.wav",
            format="wav",
            duration=7.5,
            sample_rate=44100,
            channels=1,
        )

        input_data = ChatterboxTtsTurboInput(
            text="Test voice cloning",
            audio_url=audio_artifact,
        )

        assert input_data.audio_url == audio_artifact

    def test_paralinguistic_tags_in_text(self):
        """Test that paralinguistic tags are accepted in text."""
        input_data = ChatterboxTtsTurboInput(
            text="[clear throat] Hello there [sigh] how are you [laugh]",
        )

        assert "[clear throat]" in input_data.text
        assert "[sigh]" in input_data.text
        assert "[laugh]" in input_data.text


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalChatterboxTtsTurboGenerator:
    """Tests for FalChatterboxTtsTurboGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalChatterboxTtsTurboGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-chatterbox-tts-turbo"
        assert self.generator.artifact_type == "audio"
        assert "text-to-speech" in self.generator.description.lower()
        assert "Chatterbox" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == ChatterboxTtsTurboInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = ChatterboxTtsTurboInput(
                text="Test speech generation",
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
                        format="wav",
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
        input_data = ChatterboxTtsTurboInput(
            text="Hello world, this is a test [laugh].",
            voice="lucy",
            temperature=0.8,
        )

        fake_audio_url = "https://storage.googleapis.com/falserverless/audio_output.wav"

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
                format="wav",
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
                "fal-ai/chatterbox/text-to-speech/turbo",
                arguments={
                    "text": "Hello world, this is a test [laugh].",
                    "voice": "lucy",
                    "temperature": 0.8,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_seed(self):
        """Test generation with seed parameter."""
        input_data = ChatterboxTtsTurboInput(
            text="Test with seed",
            seed=12345,
        )

        fake_audio_url = "https://storage.googleapis.com/falserverless/audio_output.wav"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-seed"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"audio": {"url": fake_audio_url}})

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="wav",
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

            await self.generator.generate(input_data, DummyCtx())

            # Verify seed is included in API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 12345

    @pytest.mark.asyncio
    async def test_generate_with_voice_cloning(self):
        """Test generation with voice cloning audio artifact."""
        audio_artifact = AudioArtifact(
            generation_id="test_audio",
            storage_url="https://example.com/voice_sample.wav",
            format="wav",
            duration=7.5,
            sample_rate=44100,
            channels=1,
        )

        input_data = ChatterboxTtsTurboInput(
            text="Test voice cloning",
            audio_url=audio_artifact,
        )

        fake_audio_url = "https://storage.googleapis.com/falserverless/audio_output.wav"
        fake_uploaded_url = "https://fal.ai/uploads/voice_sample.wav"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-clone"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"audio": {"url": fake_audio_url}})

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="wav",
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
                    return "/tmp/voice_sample.wav"

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

            # Mock upload_artifacts_to_fal in the utils module where it's defined
            with patch(
                "boards.generators.implementations.fal.utils.upload_artifacts_to_fal",
                new_callable=AsyncMock,
                return_value=[fake_uploaded_url],
            ):
                await self.generator.generate(input_data, DummyCtx())

                # Verify audio_url is included in API call
                call_args = mock_fal_client.submit_async.call_args
                assert call_args[1]["arguments"]["audio_url"] == fake_uploaded_url

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = ChatterboxTtsTurboInput(
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
        input_data = ChatterboxTtsTurboInput(
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
        input_data = ChatterboxTtsTurboInput(
            text="Test prompt for cost estimation",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Chatterbox TTS Turbo costs $0.03 per generation
        assert cost == 0.03
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_consistent(self):
        """Test cost estimation is consistent regardless of text length."""
        # Short text
        short_input = ChatterboxTtsTurboInput(text="Hi")
        short_cost = await self.generator.estimate_cost(short_input)

        # Long text
        long_input = ChatterboxTtsTurboInput(text="a" * 1000)
        long_cost = await self.generator.estimate_cost(long_input)

        # Cost should be the same (flat rate per generation)
        assert short_cost == long_cost == 0.03

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = ChatterboxTtsTurboInput.model_json_schema()

        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "voice" in schema["properties"]
        assert "audio_url" in schema["properties"]
        assert "temperature" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check text has min_length constraint
        text_prop = schema["properties"]["text"]
        assert text_prop.get("minLength") == 1

        # Check temperature constraints
        temp_prop = schema["properties"]["temperature"]
        assert temp_prop.get("minimum") == 0.05
        assert temp_prop.get("maximum") == 2.0

        # Check voice is enum
        voice_prop = schema["properties"]["voice"]
        assert "enum" in voice_prop or "anyOf" in voice_prop

    def test_different_voices(self):
        """Test generation with different voice presets."""
        voices_to_test = ["aaron", "chloe", "walter", "marisol"]

        for voice in voices_to_test:
            input_data = ChatterboxTtsTurboInput(
                text="Test",
                voice=voice,  # type: ignore[arg-type]
            )
            assert input_data.voice == voice
