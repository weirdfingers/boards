"""
Tests for FalElevenlabsTtsTurboV25Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.fal_elevenlabs_tts_turbo_v2_5 import (
    FalElevenlabsTtsTurboV25Generator,
    FalElevenlabsTtsTurboV25Input,
)


class TestFalElevenlabsTtsTurboV25Input:
    """Tests for FalElevenlabsTtsTurboV25Input schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = FalElevenlabsTtsTurboV25Input(
            text="Hello, this is a test speech.",
            voice="Rachel",
            stability=0.7,
            similarity_boost=0.8,
            style=0.5,
            speed=1.1,
            timestamps=True,
            language_code="en",
        )

        assert input_data.text == "Hello, this is a test speech."
        assert input_data.voice == "Rachel"
        assert input_data.stability == 0.7
        assert input_data.similarity_boost == 0.8
        assert input_data.style == 0.5
        assert input_data.speed == 1.1
        assert input_data.timestamps is True
        assert input_data.language_code == "en"

    def test_input_defaults(self):
        """Test default values."""
        input_data = FalElevenlabsTtsTurboV25Input(
            text="Test text",
        )

        # Check default values
        assert input_data.voice == "Rachel"
        assert input_data.stability == 0.5
        assert input_data.similarity_boost == 0.75
        assert input_data.style == 0.0
        assert input_data.speed == 1.0
        assert input_data.timestamps is False
        assert input_data.language_code is None
        assert input_data.previous_text is None
        assert input_data.next_text is None

    def test_empty_text_validation(self):
        """Test validation fails for empty text."""
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(text="")

    def test_stability_range_validation(self):
        """Test validation for stability range (0-1)."""
        # Test below minimum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                stability=-0.1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                stability=1.1,
            )

        # Test valid boundaries
        input_min = FalElevenlabsTtsTurboV25Input(text="Test", stability=0.0)
        assert input_min.stability == 0.0

        input_max = FalElevenlabsTtsTurboV25Input(text="Test", stability=1.0)
        assert input_max.stability == 1.0

    def test_similarity_boost_range_validation(self):
        """Test validation for similarity_boost range (0-1)."""
        # Test below minimum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                similarity_boost=-0.1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                similarity_boost=1.5,
            )

        # Test valid boundaries
        input_min = FalElevenlabsTtsTurboV25Input(text="Test", similarity_boost=0.0)
        assert input_min.similarity_boost == 0.0

        input_max = FalElevenlabsTtsTurboV25Input(text="Test", similarity_boost=1.0)
        assert input_max.similarity_boost == 1.0

    def test_style_range_validation(self):
        """Test validation for style range (0-1)."""
        # Test below minimum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                style=-0.1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                style=1.1,
            )

        # Test valid boundaries
        input_min = FalElevenlabsTtsTurboV25Input(text="Test", style=0.0)
        assert input_min.style == 0.0

        input_max = FalElevenlabsTtsTurboV25Input(text="Test", style=1.0)
        assert input_max.style == 1.0

    def test_speed_range_validation(self):
        """Test validation for speed range (0.7-1.2)."""
        # Test below minimum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                speed=0.6,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            FalElevenlabsTtsTurboV25Input(
                text="Test",
                speed=1.3,
            )

        # Test valid boundaries
        input_min = FalElevenlabsTtsTurboV25Input(text="Test", speed=0.7)
        assert input_min.speed == 0.7

        input_max = FalElevenlabsTtsTurboV25Input(text="Test", speed=1.2)
        assert input_max.speed == 1.2

    def test_optional_context_fields(self):
        """Test optional previous_text and next_text fields."""
        input_data = FalElevenlabsTtsTurboV25Input(
            text="Current text segment",
            previous_text="This came before",
            next_text="This comes after",
        )

        assert input_data.previous_text == "This came before"
        assert input_data.next_text == "This comes after"


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalElevenlabsTtsTurboV25Generator:
    """Tests for FalElevenlabsTtsTurboV25Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalElevenlabsTtsTurboV25Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-elevenlabs-tts-turbo-v2-5"
        assert self.generator.artifact_type == "audio"
        assert "text-to-speech" in self.generator.description.lower()
        assert "ElevenLabs" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == FalElevenlabsTtsTurboV25Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = FalElevenlabsTtsTurboV25Input(
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
        input_data = FalElevenlabsTtsTurboV25Input(
            text="Hello world, this is a test.",
            voice="Rachel",
            speed=1.0,
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
                "fal-ai/elevenlabs/tts/turbo-v2.5",
                arguments={
                    "text": "Hello world, this is a test.",
                    "voice": "Rachel",
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "speed": 1.0,
                    "timestamps": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_optional_fields(self):
        """Test successful generation with optional fields."""
        input_data = FalElevenlabsTtsTurboV25Input(
            text="Test with optional fields",
            language_code="en",
            previous_text="Previous context",
            next_text="Next context",
            timestamps=True,
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
                    },
                    "timestamps": [
                        {"word": "Test", "start": 0.0, "end": 0.5},
                    ],
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

            # Verify API call included optional fields
            call_args = mock_fal_client.submit_async.call_args[1]["arguments"]
            assert call_args["language_code"] == "en"
            assert call_args["previous_text"] == "Previous context"
            assert call_args["next_text"] == "Next context"
            assert call_args["timestamps"] is True

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = FalElevenlabsTtsTurboV25Input(
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
        input_data = FalElevenlabsTtsTurboV25Input(
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
        # Test with 100 characters
        input_data = FalElevenlabsTtsTurboV25Input(
            text="a" * 100,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Should be 100 * 0.001 = 0.1
        assert cost == 0.1
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_short_text(self):
        """Test cost estimation for short text."""
        prompt = "Hello world!"  # 12 characters
        input_data = FalElevenlabsTtsTurboV25Input(
            text=prompt,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Should be 12 * 0.001 = 0.012
        expected_cost = len(prompt) * 0.001
        assert abs(cost - expected_cost) < 0.0001
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_long_text(self):
        """Test cost estimation for long text."""
        # Test with 1000 characters
        input_data = FalElevenlabsTtsTurboV25Input(
            text="a" * 1000,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Should be 1000 * 0.001 = 1.0
        assert cost == 1.0
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = FalElevenlabsTtsTurboV25Input.model_json_schema()

        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "voice" in schema["properties"]
        assert "stability" in schema["properties"]
        assert "similarity_boost" in schema["properties"]
        assert "style" in schema["properties"]
        assert "speed" in schema["properties"]
        assert "timestamps" in schema["properties"]

        # Check text constraints
        text_prop = schema["properties"]["text"]
        assert text_prop["minLength"] == 1

        # Check numeric field constraints
        stability_prop = schema["properties"]["stability"]
        assert "minimum" in stability_prop or "ge" in stability_prop
        assert "maximum" in stability_prop or "le" in stability_prop
