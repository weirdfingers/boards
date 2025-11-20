"""
Tests for FalElevenlabsTtsElevenV3Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.elevenlabs_tts_eleven_v3 import (
    ElevenlabsTtsElevenV3Input,
    FalElevenlabsTtsElevenV3Generator,
)


class TestElevenlabsTtsElevenV3Input:
    """Tests for ElevenlabsTtsElevenV3Input schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = ElevenlabsTtsElevenV3Input(
            text="Hello, this is a test of the text to speech system.",
            voice="Sarah",
            stability=0.7,
            similarity_boost=0.8,
            style=0.3,
            speed=1.1,
            timestamps=True,
            previous_text="Previously spoken text.",
            next_text="Upcoming text to speak.",
            language_code="en-US",
        )

        assert input_data.text == "Hello, this is a test of the text to speech system."
        assert input_data.voice == "Sarah"
        assert input_data.stability == 0.7
        assert input_data.similarity_boost == 0.8
        assert input_data.style == 0.3
        assert input_data.speed == 1.1
        assert input_data.timestamps is True
        assert input_data.previous_text == "Previously spoken text."
        assert input_data.next_text == "Upcoming text to speak."
        assert input_data.language_code == "en-US"

    def test_input_defaults(self):
        """Test default values."""
        input_data = ElevenlabsTtsElevenV3Input(
            text="Test text",
        )

        # Check default values
        assert input_data.voice == "Rachel"
        assert input_data.stability == 0.5
        assert input_data.similarity_boost == 0.75
        assert input_data.style == 0.0
        assert input_data.speed == 1.0
        assert input_data.timestamps is False
        assert input_data.previous_text is None
        assert input_data.next_text is None
        assert input_data.language_code is None

    def test_text_length_validation(self):
        """Test validation for text length constraints."""
        # Test empty text (below minimum)
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(text="")

        # Test valid text
        input_data = ElevenlabsTtsElevenV3Input(text="Valid text")
        assert input_data.text == "Valid text"

    def test_stability_validation(self):
        """Test validation for stability parameter."""
        # Test stability below minimum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                stability=-0.1,
            )

        # Test stability above maximum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                stability=1.1,
            )

        # Test valid stability at boundaries
        input_data_min = ElevenlabsTtsElevenV3Input(text="Test", stability=0.0)
        assert input_data_min.stability == 0.0

        input_data_max = ElevenlabsTtsElevenV3Input(text="Test", stability=1.0)
        assert input_data_max.stability == 1.0

    def test_similarity_boost_validation(self):
        """Test validation for similarity_boost parameter."""
        # Test similarity_boost below minimum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                similarity_boost=-0.1,
            )

        # Test similarity_boost above maximum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                similarity_boost=1.1,
            )

        # Test valid similarity_boost at boundaries
        input_data_min = ElevenlabsTtsElevenV3Input(text="Test", similarity_boost=0.0)
        assert input_data_min.similarity_boost == 0.0

        input_data_max = ElevenlabsTtsElevenV3Input(text="Test", similarity_boost=1.0)
        assert input_data_max.similarity_boost == 1.0

    def test_style_validation(self):
        """Test validation for style parameter."""
        # Test style below minimum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                style=-0.1,
            )

        # Test style above maximum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                style=1.1,
            )

        # Test valid style at boundaries
        input_data_min = ElevenlabsTtsElevenV3Input(text="Test", style=0.0)
        assert input_data_min.style == 0.0

        input_data_max = ElevenlabsTtsElevenV3Input(text="Test", style=1.0)
        assert input_data_max.style == 1.0

    def test_speed_validation(self):
        """Test validation for speed parameter."""
        # Test speed below minimum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                speed=0.6,
            )

        # Test speed above maximum
        with pytest.raises(ValidationError):
            ElevenlabsTtsElevenV3Input(
                text="Test",
                speed=1.3,
            )

        # Test valid speed at boundaries
        input_data_min = ElevenlabsTtsElevenV3Input(text="Test", speed=0.7)
        assert input_data_min.speed == 0.7

        input_data_max = ElevenlabsTtsElevenV3Input(text="Test", speed=1.2)
        assert input_data_max.speed == 1.2

    def test_voice_options(self):
        """Test voice parameter accepts various voice names."""
        voices = ["Rachel", "Sarah", "Laura", "Charlie", "George", "Alice", "Daniel"]

        for voice_name in voices:
            input_data = ElevenlabsTtsElevenV3Input(
                text="Test",
                voice=voice_name,
            )
            assert input_data.voice == voice_name


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalElevenlabsTtsElevenV3Generator:
    """Tests for FalElevenlabsTtsElevenV3Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalElevenlabsTtsElevenV3Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-elevenlabs-tts-eleven-v3"
        assert self.generator.artifact_type == "audio"
        assert "text-to-speech" in self.generator.description.lower()
        assert "ElevenLabs" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == ElevenlabsTtsElevenV3Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = ElevenlabsTtsElevenV3Input(
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
        input_data = ElevenlabsTtsElevenV3Input(
            text="Hello! This is a test of the text to speech system.",
            voice="Rachel",
            stability=0.6,
            similarity_boost=0.8,
            style=0.2,
            speed=1.05,
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
                        "content_type": "audio/mpeg",
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
                "fal-ai/elevenlabs/tts/eleven-v3",
                arguments={
                    "text": "Hello! This is a test of the text to speech system.",
                    "voice": "Rachel",
                    "stability": 0.6,
                    "similarity_boost": 0.8,
                    "style": 0.2,
                    "speed": 1.05,
                    "timestamps": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_optional_context(self):
        """Test generation with optional context parameters."""
        input_data = ElevenlabsTtsElevenV3Input(
            text="Current sentence.",
            previous_text="Previous context.",
            next_text="Next context.",
            language_code="en-US",
        )

        fake_audio_url = "https://storage.googleapis.com/falserverless/audio_output.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_audio_url,
                        "content_type": "audio/mpeg",
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

            # Verify API calls include optional parameters
            call_args = mock_fal_client.submit_async.call_args[1]["arguments"]
            assert call_args["previous_text"] == "Previous context."
            assert call_args["next_text"] == "Next context."
            assert call_args["language_code"] == "en-US"

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = ElevenlabsTtsElevenV3Input(
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
        input_data = ElevenlabsTtsElevenV3Input(
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
        # Test with 1000 characters (should be $0.10)
        input_data = ElevenlabsTtsElevenV3Input(
            text="a" * 1000,
        )

        cost = await self.generator.estimate_cost(input_data)

        # $0.10 per 1000 characters
        assert cost == 0.10
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_short_text(self):
        """Test cost estimation for short text."""
        # Test with 53 characters
        prompt = "Hello! This is a test of the text to speech system."
        input_data = ElevenlabsTtsElevenV3Input(
            text=prompt,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Should be (53 / 1000) * 0.10 = 0.0053
        expected_cost = (len(prompt) / 1000.0) * 0.10
        assert abs(cost - expected_cost) < 0.0001
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_long_text(self):
        """Test cost estimation for long text."""
        # Test with 5000 characters
        input_data = ElevenlabsTtsElevenV3Input(
            text="a" * 5000,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Should be (5000 / 1000) * 0.10 = 0.50
        assert cost == 0.50
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = ElevenlabsTtsElevenV3Input.model_json_schema()

        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "voice" in schema["properties"]
        assert "stability" in schema["properties"]
        assert "similarity_boost" in schema["properties"]
        assert "style" in schema["properties"]
        assert "speed" in schema["properties"]
        assert "timestamps" in schema["properties"]
        assert "previous_text" in schema["properties"]
        assert "next_text" in schema["properties"]
        assert "language_code" in schema["properties"]

        # Check text constraints
        text_prop = schema["properties"]["text"]
        assert text_prop["minLength"] == 1

        # Check numeric constraints
        stability_prop = schema["properties"]["stability"]
        assert stability_prop["minimum"] == 0.0
        assert stability_prop["maximum"] == 1.0

        speed_prop = schema["properties"]["speed"]
        assert speed_prop["minimum"] == 0.7
        assert speed_prop["maximum"] == 1.2
