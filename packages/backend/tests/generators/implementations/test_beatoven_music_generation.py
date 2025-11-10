"""
Tests for FalBeatovenMusicGenerationGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.beatoven_music_generation import (
    BeatovenMusicGenerationInput,
    FalBeatovenMusicGenerationGenerator,
)


class TestBeatovenMusicGenerationInput:
    """Tests for BeatovenMusicGenerationInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Upbeat electronic music with synthesizers and driving bass"
        )

        assert input_data.prompt == "Upbeat electronic music with synthesizers and driving bass"
        assert input_data.duration == 90  # Default
        assert input_data.refinement == 100  # Default
        assert input_data.creativity == 16  # Default
        assert input_data.seed is None  # Default
        assert input_data.negative_prompt == ""  # Default

    def test_input_with_all_parameters(self):
        """Test input with all custom parameters."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Jazz music for a late-night restaurant setting",
            duration=60,
            refinement=150,
            creativity=18,
            seed=12345,
            negative_prompt="heavy drums, distortion",
        )

        assert input_data.prompt == "Jazz music for a late-night restaurant setting"
        assert input_data.duration == 60
        assert input_data.refinement == 150
        assert input_data.creativity == 18
        assert input_data.seed == 12345
        assert input_data.negative_prompt == "heavy drums, distortion"

    def test_input_defaults(self):
        """Test default values."""
        input_data = BeatovenMusicGenerationInput(prompt="Test music")

        assert input_data.duration == 90
        assert input_data.refinement == 100
        assert input_data.creativity == 16
        assert input_data.seed is None
        assert input_data.negative_prompt == ""

    def test_duration_validation_min(self):
        """Test validation fails for duration below minimum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                duration=4,  # Below minimum of 5
            )

    def test_duration_validation_max(self):
        """Test validation fails for duration above maximum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                duration=151,  # Above maximum of 150
            )

    def test_duration_exactly_min(self):
        """Test duration with exactly minimum value (5 seconds)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            duration=5,
        )
        assert input_data.duration == 5

    def test_duration_exactly_max(self):
        """Test duration with exactly maximum value (150 seconds)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            duration=150,
        )
        assert input_data.duration == 150

    def test_refinement_validation_min(self):
        """Test validation fails for refinement below minimum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                refinement=9,  # Below minimum of 10
            )

    def test_refinement_validation_max(self):
        """Test validation fails for refinement above maximum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                refinement=201,  # Above maximum of 200
            )

    def test_refinement_exactly_min(self):
        """Test refinement with exactly minimum value (10)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            refinement=10,
        )
        assert input_data.refinement == 10

    def test_refinement_exactly_max(self):
        """Test refinement with exactly maximum value (200)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            refinement=200,
        )
        assert input_data.refinement == 200

    def test_creativity_validation_min(self):
        """Test validation fails for creativity below minimum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                creativity=0,  # Below minimum of 1
            )

    def test_creativity_validation_max(self):
        """Test validation fails for creativity above maximum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                creativity=21,  # Above maximum of 20
            )

    def test_creativity_exactly_min(self):
        """Test creativity with exactly minimum value (1)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            creativity=1,
        )
        assert input_data.creativity == 1

    def test_creativity_exactly_max(self):
        """Test creativity with exactly maximum value (20)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            creativity=20,
        )
        assert input_data.creativity == 20

    def test_seed_validation_min(self):
        """Test validation fails for seed below minimum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                seed=-1,  # Below minimum of 0
            )

    def test_seed_validation_max(self):
        """Test validation fails for seed above maximum."""
        with pytest.raises(ValidationError):
            BeatovenMusicGenerationInput(
                prompt="Test",
                seed=2147483648,  # Above maximum of 2147483647
            )

    def test_seed_exactly_min(self):
        """Test seed with exactly minimum value (0)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            seed=0,
        )
        assert input_data.seed == 0

    def test_seed_exactly_max(self):
        """Test seed with exactly maximum value (2147483647)."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            seed=2147483647,
        )
        assert input_data.seed == 2147483647

    def test_seed_none(self):
        """Test seed can be None for random generation."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test",
            seed=None,
        )
        assert input_data.seed is None


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalBeatovenMusicGenerationGenerator:
    """Tests for FalBeatovenMusicGenerationGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalBeatovenMusicGenerationGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "beatoven-music-generation"
        assert self.generator.artifact_type == "audio"
        assert "Beatoven" in self.generator.description
        assert "music" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == BeatovenMusicGenerationInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = BeatovenMusicGenerationInput(
                prompt="Test music prompt"
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
        """Test successful generation with all parameters."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Lush, ambient soundscape with serene sounds and melancholic piano",
            duration=60,
            refinement=120,
            creativity=18,
            seed=42,
            negative_prompt="heavy drums, distortion",
        )

        fake_output_url = "https://v3.fal.media/files/beatoven/test-output.wav"

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
                        "content_type": "audio/wav",
                        "file_size": 5120000,
                        "file_name": "output.wav",
                    },
                    "prompt": "Lush, ambient soundscape with serene sounds and melancholic piano",
                    "metadata": {
                        "duration": 60,
                        "sample_rate": 44100,
                    },
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
                format="wav",
                sample_rate=None,
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
                "beatoven/music-generation",
                arguments={
                    "prompt": "Lush, ambient soundscape with serene sounds and melancholic piano",
                    "duration": 60,
                    "refinement": 120,
                    "creativity": 18,
                    "seed": 42,
                    "negative_prompt": "heavy drums, distortion",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_minimal_parameters(self):
        """Test successful generation with only required parameters."""
        input_data = BeatovenMusicGenerationInput(
            prompt="House music with synthesizers, driving bass and 4/4 beat",
        )

        fake_output_url = "https://v3.fal.media/files/beatoven/minimal-output.wav"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_output_url,
                        "content_type": "audio/wav",
                        "file_size": 7680000,
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                format="wav",
                sample_rate=None,
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

            # Verify API call includes defaults and excludes empty optional fields
            call_args = mock_fal_client.submit_async.call_args
            arguments = call_args[1]["arguments"]
            assert arguments["prompt"] == "House music with synthesizers, driving bass and 4/4 beat"
            assert arguments["duration"] == 90
            assert arguments["refinement"] == 100
            assert arguments["creativity"] == 16
            assert "seed" not in arguments  # None should not be included
            assert "negative_prompt" not in arguments  # Empty string should not be included

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = BeatovenMusicGenerationInput(
            prompt="Test music prompt"
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
        input_data = BeatovenMusicGenerationInput(
            prompt="Test music prompt"
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-999"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "content_type": "audio/wav",
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
        input_data = BeatovenMusicGenerationInput(
            prompt="Test music prompt"
        )

        cost = await self.generator.estimate_cost(input_data)

        # Cost is $0.05 per generation
        assert cost == 0.05
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = BeatovenMusicGenerationInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "refinement" in schema["properties"]
        assert "creativity" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "negative_prompt" in schema["properties"]

        # Check duration constraints
        duration_prop = schema["properties"]["duration"]
        assert duration_prop["minimum"] == 5
        assert duration_prop["maximum"] == 150
        assert duration_prop["default"] == 90

        # Check refinement constraints
        refinement_prop = schema["properties"]["refinement"]
        assert refinement_prop["minimum"] == 10
        assert refinement_prop["maximum"] == 200
        assert refinement_prop["default"] == 100

        # Check creativity constraints
        creativity_prop = schema["properties"]["creativity"]
        assert creativity_prop["minimum"] == 1
        assert creativity_prop["maximum"] == 20
        assert creativity_prop["default"] == 16

        # Check seed constraints
        seed_prop = schema["properties"]["seed"]
        assert seed_prop["anyOf"][0]["type"] == "integer"
        assert seed_prop["anyOf"][0]["minimum"] == 0
        assert seed_prop["anyOf"][0]["maximum"] == 2147483647

        # Check required fields
        assert "prompt" in schema["required"]
