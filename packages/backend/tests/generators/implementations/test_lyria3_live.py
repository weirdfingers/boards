"""
Live API tests for FalLyria3Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_lyria3_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_lyria3_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.lyria3 import (
    FalLyria3Generator,
    Lyria3Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestLyria3GeneratorLive:
    """Live API tests for FalLyria3Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalLyria3Generator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic music generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a simple prompt to reduce cost.
        """
        inputs = Lyria3Input(
            prompt="Simple acoustic guitar melody, calm and peaceful",
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
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = Lyria3Input(prompt="Test")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate matches documented pricing
        assert estimated_cost == 0.04

        # Sanity check on absolute cost
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0
