"""
Live API tests for KieGrokImagineExtendGenerator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_grok_imagine_extend_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_grok_imagine_extend_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v

Note: These tests require a valid task_id from a previously completed
Kie.ai Grok Imagine video generation task.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import VideoArtifact
from boards.generators.implementations.kie.video.grok_imagine_extend import (
    GrokImagineExtendInput,
    KieGrokImagineExtendGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


class TestGrokImagineExtendGeneratorLive:
    """Live API tests for KieGrokImagineExtendGenerator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieGrokImagineExtendGenerator()
        # Sync API keys from settings to os.environ for use in generator
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_extend_6s(self, skip_if_no_kie_key, dummy_context, cost_logger):
        """
        Test basic 6-second video extension.

        This test makes a real API call to Kie.ai and will consume credits.
        Requires a valid task_id from a previous Grok Imagine generation.

        NOTE: You must replace the task_id below with a valid one from your
        Kie.ai account before running this test.
        """
        # Replace with a valid task_id from a completed Grok Imagine generation
        test_task_id = "REPLACE_WITH_VALID_TASK_ID"

        if test_task_id == "REPLACE_WITH_VALID_TASK_ID":
            pytest.skip("No valid task_id provided for live test")

        inputs = GrokImagineExtendInput(
            task_id=test_task_id,
            prompt="The camera slowly pans forward revealing more of the scene",
            extend_times="6",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.format == "mp4"
        assert artifact.storage_url.startswith("http")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_kie_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Test 6s extension
        inputs_6s = GrokImagineExtendInput(
            task_id="task_123",
            prompt="test",
            extend_times="6",
        )
        cost_6s = await self.generator.estimate_cost(inputs_6s)
        assert cost_6s > 0.0
        assert cost_6s < 0.50  # Sanity check
        assert cost_6s == 0.10

        # Test 10s extension
        inputs_10s = GrokImagineExtendInput(
            task_id="task_123",
            prompt="test",
            extend_times="10",
        )
        cost_10s = await self.generator.estimate_cost(inputs_10s)
        assert cost_10s > 0.0
        assert cost_10s < 0.50  # Sanity check
        assert cost_10s == 0.15

        # 10s should cost more than 6s
        assert cost_10s > cost_6s
