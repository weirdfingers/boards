"""
Live API tests for FalChatterboxTtsTurboGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_chatterbox_tts_turbo_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_chatterbox_tts_turbo_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.chatterbox_tts_turbo import (
    ChatterboxTtsTurboInput,
    FalChatterboxTtsTurboGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestChatterboxTtsTurboGeneratorLive:
    """Live API tests for FalChatterboxTtsTurboGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalChatterboxTtsTurboGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic speech generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Use short text to minimize cost
        inputs = ChatterboxTtsTurboInput(
            text="Hello.",  # Very short to reduce cost
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
        assert artifact.format == "wav"

    @pytest.mark.asyncio
    async def test_generate_with_different_voice(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with a different voice preset.

        Verifies that voice parameter is correctly processed.
        """
        # Use short text to minimize cost
        inputs = ChatterboxTtsTurboInput(
            text="Testing voice.",
            voice="walter",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None
        assert artifact.format == "wav"

    @pytest.mark.asyncio
    async def test_generate_with_paralinguistic_tags(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with paralinguistic tags.

        Verifies that inline tags like [laugh], [sigh] are processed.
        """
        # Use text with paralinguistic tag
        inputs = ChatterboxTtsTurboInput(
            text="Ha [laugh] that's funny.",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None

    @pytest.mark.asyncio
    async def test_generate_with_temperature(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test speech generation with custom temperature.

        Verifies that temperature parameter affects generation.
        """
        inputs = ChatterboxTtsTurboInput(
            text="Testing temperature.",
            temperature=1.2,  # Higher temperature for more variation
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = ChatterboxTtsTurboInput(text="Test")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 0.10  # Should be well under $0.10 per generation
        assert estimated_cost == 0.03  # Expected flat rate
