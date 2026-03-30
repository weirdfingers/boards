"""
Live API tests for KieSunoV55Generator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_suno_v5_5_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_suno_v5_5_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact
from boards.generators.implementations.kie.audio.suno_v5_5 import (
    KieSunoV55Generator,
    SunoV55Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


class TestKieSunoV55GeneratorLive:
    """Live API tests for KieSunoV55Generator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieSunoV55Generator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic_song(self, skip_if_no_kie_key, dummy_context, cost_logger):
        """
        Test basic music generation with lyrics.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal parameters to reduce cost.
        """
        inputs = SunoV55Input(
            title="Test Song",
            style="simple acoustic pop",
            lyrics="Hello world, this is a test song",
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, dummy_context)

        assert result.outputs is not None
        assert len(result.outputs) >= 1

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("http")
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_generate_instrumental(self, skip_if_no_kie_key, dummy_context, cost_logger):
        """
        Test instrumental music generation.

        This test makes a real API call to Kie.ai and will consume credits.
        """
        inputs = SunoV55Input(
            title="Chill Instrumental",
            style="lo-fi hip hop with jazzy piano",
            instrumental=True,
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, dummy_context)

        assert result.outputs is not None
        assert len(result.outputs) >= 1

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("http")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_kie_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = SunoV55Input(
            title="Test",
            style="pop",
        )
        estimated_cost = await self.generator.estimate_cost(inputs)
        assert estimated_cost == 0.06
        assert estimated_cost > 0.0
        assert estimated_cost < 0.20  # Sanity check
