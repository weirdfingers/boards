"""
Live API tests for KieNanoBananaEditGenerator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_nano_banana_edit_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_nano_banana_edit_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.kie.image.nano_banana_edit import (
    KieNanoBananaEditGenerator,
    NanoBananaEditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


class TestKieNanoBananaEditGeneratorLive:
    """Live API tests for KieNanoBananaEditGenerator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieNanoBananaEditGenerator()
        # Sync API keys from settings to os.environ for use in generator
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_kie_key, image_resolving_context, cost_logger):
        """
        Test basic generation with minimal parameters.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Create test image artifact (use a small public image)
        test_image = ImageArtifact(
            generation_id="test_input",
            storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
            format="png",
            width=256,
            height=256,
        )

        # Create minimal input to reduce cost
        inputs = NanoBananaEditInput(
            prompt="make it blue",  # Simple prompt
            image_sources=[test_image],  # Single image
            output_format="png",
            image_size="1:1",  # Smallest aspect ratio
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert artifact.storage_url is not None
        assert artifact.format == "png"
        # Verify URL is accessible (basic check - starts with http)
        assert artifact.storage_url.startswith("http")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_kie_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        test_image = ImageArtifact(
            generation_id="test_input",
            storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
            format="png",
            width=256,
            height=256,
        )

        inputs = NanoBananaEditInput(
            prompt="test",
            image_sources=[test_image],
        )

        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        # Should be around $0.025 per image
        assert estimated_cost > 0.0
        assert estimated_cost < 0.10  # Sanity check - should be less than $0.10
        assert estimated_cost == 0.025  # Verify exact cost matches our estimate
