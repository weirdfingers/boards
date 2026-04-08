"""
Live API tests for KieSunoSoundsGenerator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_suno_sounds_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_suno_sounds_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v
"""

import os

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.kie.audio.suno_sounds import (
    KieSunoSoundsGenerator,
    SunoSoundsInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


@pytest.fixture
def skip_if_no_kie_key():
    """Skip test if KIE_API_KEY is not available."""
    if not os.getenv("KIE_API_KEY"):
        pytest.skip("KIE_API_KEY not set - skipping live API test")


class TestSunoSoundsGeneratorLive:
    """Live API tests for KieSunoSoundsGenerator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieSunoSoundsGenerator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_kie_key, dummy_context, cost_logger):
        """
        Test basic sound generation with minimal parameters.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        estimated_cost = await self.generator.estimate_cost(SunoSoundsInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        inputs = SunoSoundsInput(
            prompt="gentle rain on a tin roof",
        )

        result = await self.generator.generate(inputs, dummy_context)

        assert result.outputs is not None
        assert len(result.outputs) >= 1

        artifact = result.outputs[0]
        assert artifact.storage_url is not None
        assert artifact.format == "mp3"
