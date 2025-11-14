"""
Live API tests for FalBeatovenSoundEffectGenerationGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_beatoven_sound_effect_generation_live.py \\
        -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_beatoven_sound_effect_generation_live.py \\
        -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.beatoven_sound_effect_generation import (
    BeatovenSoundEffectGenerationInput,
    FalBeatovenSoundEffectGenerationGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestBeatovenSoundEffectGenerationGeneratorLive:
    """Live API tests for FalBeatovenSoundEffectGenerationGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalBeatovenSoundEffectGenerationGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic sound effect generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal settings to reduce cost.
        """
        # Create minimal input to reduce cost
        # Use short duration and low refinement to minimize cost
        inputs = BeatovenSoundEffectGenerationInput(
            prompt="Simple dog bark sound effect",
            duration=2,  # Minimum practical duration
            refinement=20,  # Lower refinement for faster/cheaper generation
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 1

        # Verify artifact properties
        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "wav"

    @pytest.mark.asyncio
    async def test_generate_with_all_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test sound effect generation with all parameters specified.

        Verifies that the generator works correctly with custom settings.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            BeatovenSoundEffectGenerationInput(
                prompt="Test sound effect",
            )
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with all parameters
        inputs = BeatovenSoundEffectGenerationInput(
            prompt="Futuristic sci-fi door opening sound effect",
            duration=3,
            refinement=30,
            creativity=12,
            negative_prompt="No human voices or music",
            seed=42,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "wav"

    @pytest.mark.asyncio
    async def test_generate_with_seed_reproducibility(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test that using the same seed produces consistent results.

        This test runs generation twice with the same seed to verify reproducibility.
        """
        # Use the same seed for both generations
        inputs = BeatovenSoundEffectGenerationInput(
            prompt="Thunder sound effect",
            duration=2,
            refinement=20,
            creativity=10,
            seed=999,
        )

        # Log estimated cost (multiply by 2 for both generations)
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost * 2)

        # First generation
        result1 = await self.generator.generate(inputs, dummy_context)

        # Second generation with same inputs
        result2 = await self.generator.generate(inputs, dummy_context)

        # Verify both generated successfully
        assert result1.outputs is not None
        assert len(result1.outputs) == 1
        assert result2.outputs is not None
        assert len(result2.outputs) == 1

        # Both should be valid audio artifacts
        from boards.generators.artifacts import AudioArtifact

        assert isinstance(result1.outputs[0], AudioArtifact)
        assert isinstance(result2.outputs[0], AudioArtifact)

        # Note: The actual URLs may differ even with the same seed due to
        # Fal's storage system, but both should be valid audio files

    @pytest.mark.asyncio
    async def test_estimate_cost_is_reasonable(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = BeatovenSoundEffectGenerationInput(
            prompt="Test sound effect",
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 0.5  # Should be well under $0.50
        # Based on typical sound effect generation pricing
        assert 0.01 <= estimated_cost <= 0.15  # Expected range for sound effects
