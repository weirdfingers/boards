"""
Tests for FalChatterboxTextToSpeechGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.chatterbox_text_to_speech import (
    ChatterboxTextToSpeechInput,
    FalChatterboxTextToSpeechGenerator,
)


class TestChatterboxTextToSpeechInput:
    """Tests for ChatterboxTextToSpeechInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = ChatterboxTextToSpeechInput(
            text="Hello, this is a test speech.",
            audio_url="https://example.com/voice.mp3",
            exaggeration=0.5,
            temperature=1.0,
            cfg=0.7,
            seed=42,
        )

        assert input_data.text == "Hello, this is a test speech."
        assert input_data.audio_url == "https://example.com/voice.mp3"
        assert input_data.exaggeration == 0.5
        assert input_data.temperature == 1.0
        assert input_data.cfg == 0.7
        assert input_data.seed == 42

    def test_input_defaults(self):
        """Test default values."""
        input_data = ChatterboxTextToSpeechInput(
            text="Test prompt",
        )

        assert input_data.text == "Test prompt"
        assert input_data.audio_url is None
        assert input_data.exaggeration == 0.25
        assert input_data.temperature == 0.7
        assert input_data.cfg == 0.5
        assert input_data.seed is None

    def test_input_with_emotive_tags(self):
        """Test input with emotive tags."""
        input_data = ChatterboxTextToSpeechInput(
            text="I just won the lottery! <laugh> Can you believe it? <gasp>",
        )

        assert "<laugh>" in input_data.text
        assert "<gasp>" in input_data.text

    def test_empty_text_validation(self):
        """Test validation fails for empty text."""
        with pytest.raises(ValidationError):
            ChatterboxTextToSpeechInput(text="")

    def test_exaggeration_validation(self):
        """Test validation for exaggeration range (0.0 to 1.0)."""
        # Valid minimum
        input_data = ChatterboxTextToSpeechInput(text="Test", exaggeration=0.0)
        assert input_data.exaggeration == 0.0

        # Valid maximum
        input_data = ChatterboxTextToSpeechInput(text="Test", exaggeration=1.0)
        assert input_data.exaggeration == 1.0

        # Below minimum
        with pytest.raises(ValidationError):
            ChatterboxTextToSpeechInput(text="Test", exaggeration=-0.1)

        # Above maximum
        with pytest.raises(ValidationError):
            ChatterboxTextToSpeechInput(text="Test", exaggeration=1.1)

    def test_temperature_validation(self):
        """Test validation for temperature range (0.05 to 2.0)."""
        # Valid minimum
        input_data = ChatterboxTextToSpeechInput(text="Test", temperature=0.05)
        assert input_data.temperature == 0.05

        # Valid maximum
        input_data = ChatterboxTextToSpeechInput(text="Test", temperature=2.0)
        assert input_data.temperature == 2.0

        # Below minimum
        with pytest.raises(ValidationError):
            ChatterboxTextToSpeechInput(text="Test", temperature=0.01)

        # Above maximum
        with pytest.raises(ValidationError):
            ChatterboxTextToSpeechInput(text="Test", temperature=2.5)

    def test_cfg_validation(self):
        """Test validation for cfg range (0.1 to 1.0)."""
        # Valid minimum
        input_data = ChatterboxTextToSpeechInput(text="Test", cfg=0.1)
        assert input_data.cfg == 0.1

        # Valid maximum
        input_data = ChatterboxTextToSpeechInput(text="Test", cfg=1.0)
        assert input_data.cfg == 1.0

        # Below minimum
        with pytest.raises(ValidationError):
            ChatterboxTextToSpeechInput(text="Test", cfg=0.05)

        # Above maximum
        with pytest.raises(ValidationError):
            ChatterboxTextToSpeechInput(text="Test", cfg=1.5)


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalChatterboxTextToSpeechGenerator:
    """Tests for FalChatterboxTextToSpeechGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalChatterboxTextToSpeechGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-chatterbox-text-to-speech"
        assert self.generator.artifact_type == "audio"
        assert "Chatterbox" in self.generator.description
        assert "text-to-speech" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == ChatterboxTextToSpeechInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = ChatterboxTextToSpeechInput(
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
        input_data = ChatterboxTextToSpeechInput(
            text="Hello world, this is a test.",
            exaggeration=0.3,
            temperature=0.8,
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
                "fal-ai/chatterbox/text-to-speech",
                arguments={
                    "text": "Hello world, this is a test.",
                    "exaggeration": 0.3,
                    "temperature": 0.8,
                    "cfg": 0.5,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_all_parameters(self):
        """Test generation with all optional parameters."""
        input_data = ChatterboxTextToSpeechInput(
            text="Test with all params",
            audio_url="https://example.com/voice.mp3",
            exaggeration=0.5,
            temperature=1.0,
            cfg=0.7,
            seed=12345,
        )

        fake_audio_url = "https://storage.googleapis.com/falserverless/audio_output.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"audio": {"url": fake_audio_url}})

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

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify all parameters were passed
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/chatterbox/text-to-speech",
                arguments={
                    "text": "Test with all params",
                    "audio_url": "https://example.com/voice.mp3",
                    "exaggeration": 0.5,
                    "temperature": 1.0,
                    "cfg": 0.7,
                    "seed": 12345,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = ChatterboxTextToSpeechInput(
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
        input_data = ChatterboxTextToSpeechInput(
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
        input_data = ChatterboxTextToSpeechInput(
            text="Hello world, this is a test.",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Chatterbox has a fixed cost of $0.03 per generation
        assert cost == 0.03
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_long_text(self):
        """Test cost estimation for long text."""
        # Even with long text, cost should be fixed
        input_data = ChatterboxTextToSpeechInput(
            text="a" * 1000,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Fixed cost regardless of text length
        assert cost == 0.03
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = ChatterboxTextToSpeechInput.model_json_schema()

        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "audio_url" in schema["properties"]
        assert "exaggeration" in schema["properties"]
        assert "temperature" in schema["properties"]
        assert "cfg" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check text constraints
        text_prop = schema["properties"]["text"]
        assert text_prop["minLength"] == 1

        # Check exaggeration constraints
        exag_prop = schema["properties"]["exaggeration"]
        assert exag_prop["minimum"] == 0.0
        assert exag_prop["maximum"] == 1.0

        # Check temperature constraints
        temp_prop = schema["properties"]["temperature"]
        assert temp_prop["minimum"] == 0.05
        assert temp_prop["maximum"] == 2.0

        # Check cfg constraints
        cfg_prop = schema["properties"]["cfg"]
        assert cfg_prop["minimum"] == 0.1
        assert cfg_prop["maximum"] == 1.0
