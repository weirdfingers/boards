"""
Live API tests for FalBeatovenMusicGenerationGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_beatoven_music_generation_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_beatoven_music_generation_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.beatoven_music_generation import (
    BeatovenMusicGenerationInput,
    FalBeatovenMusicGenerationGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestBeatovenMusicGenerationGeneratorLive:
    """Live API tests for FalBeatovenMusicGenerationGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalBeatovenMusicGenerationGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic music generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal settings to reduce cost.
        """
        # Create minimal input to reduce cost
        # Use short duration and default quality settings
        inputs = BeatovenMusicGenerationInput(
            prompt="Simple upbeat electronic music for testing",
            duration=5,  # Minimum duration to reduce cost
            refinement=50,  # Lower refinement to reduce processing time
            creativity=10,  # Moderate creativity
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
        Test music generation with all optional parameters.

        Verifies that the generator works correctly with seed and negative_prompt.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            BeatovenMusicGenerationInput(
                prompt="Test music prompt",
            )
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with all parameters
        inputs = BeatovenMusicGenerationInput(
            prompt="Jazz music for a late-night restaurant setting",
            duration=10,  # Short duration to reduce cost
            refinement=80,
            creativity=15,
            seed=42,  # Fixed seed for reproducibility
            negative_prompt="heavy drums, distortion",
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
    async def test_estimate_cost_is_reasonable(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = BeatovenMusicGenerationInput(
            prompt="Test music prompt",
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1.00
        # Based on typical music generation pricing
        assert 0.01 <= estimated_cost <= 0.15  # Expected range for music generation
