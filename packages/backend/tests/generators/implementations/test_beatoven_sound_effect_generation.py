"""
Tests for FalBeatovenSoundEffectGenerationGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.beatoven_sound_effect_generation import (
    BeatovenSoundEffectGenerationInput,
    FalBeatovenSoundEffectGenerationGenerator,
)


class TestBeatovenSoundEffectGenerationInput:
    """Tests for BeatovenSoundEffectGenerationInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Thunder and lightning sound effect",
        )

        assert input_data.prompt == "Thunder and lightning sound effect"
        assert input_data.duration == 5  # default
        assert input_data.refinement == 40  # default
        assert input_data.creativity == 16  # default
        assert input_data.negative_prompt == ""  # default
        assert input_data.seed is None  # default

    def test_input_with_all_parameters(self):
        """Test input with all custom parameters."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Futuristic sci-fi spaceship engine sound",
            duration=10.5,
            refinement=100,
            creativity=18,
            negative_prompt="No music or voices",
            seed=42,
        )

        assert input_data.prompt == "Futuristic sci-fi spaceship engine sound"
        assert input_data.duration == 10.5
        assert input_data.refinement == 100
        assert input_data.creativity == 18
        assert input_data.negative_prompt == "No music or voices"
        assert input_data.seed == 42

    def test_input_defaults(self):
        """Test default values."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound effect",
        )

        assert input_data.duration == 5
        assert input_data.refinement == 40
        assert input_data.creativity == 16
        assert input_data.negative_prompt == ""
        assert input_data.seed is None

    def test_duration_min_validation(self):
        """Test validation fails for duration below minimum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                duration=0.5,  # Less than 1
            )

    def test_duration_max_validation(self):
        """Test validation fails for duration above maximum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                duration=40,  # Greater than 35
            )

    def test_duration_min_boundary(self):
        """Test duration at minimum boundary (1 second)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            duration=1,
        )
        assert input_data.duration == 1

    def test_duration_max_boundary(self):
        """Test duration at maximum boundary (35 seconds)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            duration=35,
        )
        assert input_data.duration == 35

    def test_refinement_min_validation(self):
        """Test validation fails for refinement below minimum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                refinement=5,  # Less than 10
            )

    def test_refinement_max_validation(self):
        """Test validation fails for refinement above maximum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                refinement=250,  # Greater than 200
            )

    def test_refinement_min_boundary(self):
        """Test refinement at minimum boundary (10)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            refinement=10,
        )
        assert input_data.refinement == 10

    def test_refinement_max_boundary(self):
        """Test refinement at maximum boundary (200)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            refinement=200,
        )
        assert input_data.refinement == 200

    def test_creativity_min_validation(self):
        """Test validation fails for creativity below minimum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                creativity=0.5,  # Less than 1
            )

    def test_creativity_max_validation(self):
        """Test validation fails for creativity above maximum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                creativity=25,  # Greater than 20
            )

    def test_creativity_min_boundary(self):
        """Test creativity at minimum boundary (1)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            creativity=1,
        )
        assert input_data.creativity == 1

    def test_creativity_max_boundary(self):
        """Test creativity at maximum boundary (20)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            creativity=20,
        )
        assert input_data.creativity == 20

    def test_seed_min_validation(self):
        """Test validation fails for seed below minimum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                seed=-1,  # Less than 0
            )

    def test_seed_max_validation(self):
        """Test validation fails for seed above maximum."""
        with pytest.raises(ValidationError):
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound",
                seed=2147483648,  # Greater than 2147483647
            )

    def test_seed_min_boundary(self):
        """Test seed at minimum boundary (0)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            seed=0,
        )
        assert input_data.seed == 0

    def test_seed_max_boundary(self):
        """Test seed at maximum boundary (2147483647)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            seed=2147483647,
        )
        assert input_data.seed == 2147483647

    def test_seed_none_allowed(self):
        """Test that seed can be None."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound",
            seed=None,
        )
        assert input_data.seed is None


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalBeatovenSoundEffectGenerationGenerator:
    """Tests for FalBeatovenSoundEffectGenerationGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalBeatovenSoundEffectGenerationGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-beatoven-sound-effect-generation"
        assert self.generator.artifact_type == "audio"
        assert "sound effect" in self.generator.description.lower()
        assert "Beatoven" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == BeatovenSoundEffectGenerationInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = BeatovenSoundEffectGenerationInput(
                prompt="Test sound effect",
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
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Dramatic thunder and lightning storm sound effect",
            duration=8,
            refinement=60,
            creativity=15,
            negative_prompt="No music",
            seed=123,
        )

        fake_output_url = "https://v3.fal.media/files/lion/beatoven-output.wav"

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
                        "file_size": 1536000,
                        "file_name": "output.wav",
                    },
                    "prompt": "Dramatic thunder and lightning storm sound effect",
                    "metadata": {
                        "duration": 8,
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
                "beatoven/sound-effect-generation",
                arguments={
                    "prompt": "Dramatic thunder and lightning storm sound effect",
                    "duration": 8,
                    "refinement": 60,
                    "creativity": 15,
                    "negative_prompt": "No music",
                    "seed": 123,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_minimal_params(self):
        """Test successful generation with minimal parameters (only prompt)."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Simple dog bark sound effect",
        )

        fake_output_url = "https://v3.fal.media/files/lion/beatoven-output2.wav"

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
                        "file_size": 960000,
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

            # Verify API call doesn't include seed when None
            call_args = mock_fal_client.submit_async.call_args
            assert "seed" not in call_args[1]["arguments"]
            # But includes other default values
            assert call_args[1]["arguments"]["duration"] == 5
            assert call_args[1]["arguments"]["refinement"] == 40
            assert call_args[1]["arguments"]["creativity"] == 16

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound effect",
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
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound effect",
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
        input_data = BeatovenSoundEffectGenerationInput(
            prompt="Test sound effect",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Cost is $0.05 per generation
        assert cost == 0.05
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = BeatovenSoundEffectGenerationInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "refinement" in schema["properties"]
        assert "creativity" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check duration constraints
        duration_prop = schema["properties"]["duration"]
        assert duration_prop["minimum"] == 1
        assert duration_prop["maximum"] == 35

        # Check refinement constraints
        refinement_prop = schema["properties"]["refinement"]
        assert refinement_prop["minimum"] == 10
        assert refinement_prop["maximum"] == 200

        # Check creativity constraints
        creativity_prop = schema["properties"]["creativity"]
        assert creativity_prop["minimum"] == 1
        assert creativity_prop["maximum"] == 20

        # Check seed constraints
        seed_prop = schema["properties"]["seed"]
        assert seed_prop.get("anyOf") or seed_prop.get("minimum") == 0

        # Check required fields
        assert "prompt" in schema["required"]
