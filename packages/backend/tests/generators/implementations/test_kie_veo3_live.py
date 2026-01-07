"""
Live API tests for KieVeo3Generator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_veo3_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_veo3_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.kie.video.veo3 import (
    KieVeo3Generator,
    KieVeo3Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


class TestKieVeo3GeneratorLive:
    """Live API tests for KieVeo3Generator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieVeo3Generator()
        # Sync API keys from settings to os.environ for use in generator
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_text_to_video_basic(
        self, skip_if_no_kie_key, dummy_context, cost_logger
    ):
        """
        Test basic text-to-video generation.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Create minimal input to reduce cost
        inputs = KieVeo3Input(
            prompt="a red ball rolling down a hill",  # Simple prompt
            aspect_ratio="16:9",
            model="veo3_fast",  # Use fast model for lower cost
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
        assert artifact.storage_url is not None
        assert artifact.format == "mp4"
        assert artifact.width == 1920
        assert artifact.height == 1080
        assert artifact.duration == 8.0
        # Verify URL is accessible (basic check - starts with http)
        assert artifact.storage_url.startswith("http")

    @pytest.mark.asyncio
    async def test_generate_image_to_video_basic(
        self, skip_if_no_kie_key, image_resolving_context, cost_logger
    ):
        """
        Test basic image-to-video generation.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Use a small public image
        test_image = ImageArtifact(
            generation_id="test_input",
            storage_url="https://placehold.co/512x512/ff0000/ff0000.png",
            format="png",
            width=512,
            height=512,
        )

        # Create minimal input to reduce cost
        inputs = KieVeo3Input(
            prompt="make the red square move to the right",
            image_sources=[test_image],
            aspect_ratio="16:9",
            model="veo3_fast",  # Use fast model for lower cost
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
        assert artifact.format == "mp4"
        # Verify URL is accessible (basic check - starts with http)
        assert artifact.storage_url.startswith("http")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_kie_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Test veo3 model
        inputs_veo3 = KieVeo3Input(
            prompt="test",
            model="veo3",
        )
        estimated_cost_veo3 = await self.generator.estimate_cost(inputs_veo3)
        assert estimated_cost_veo3 > 0.0
        assert estimated_cost_veo3 < 0.20  # Sanity check
        assert estimated_cost_veo3 == 0.08  # Verify exact cost matches our estimate

        # Test veo3_fast model
        inputs_fast = KieVeo3Input(
            prompt="test",
            model="veo3_fast",
        )
        estimated_cost_fast = await self.generator.estimate_cost(inputs_fast)
        assert estimated_cost_fast > 0.0
        assert estimated_cost_fast < 0.10  # Sanity check
        assert estimated_cost_fast == 0.04  # Verify exact cost matches our estimate

        # veo3_fast should be cheaper than veo3
        assert estimated_cost_fast < estimated_cost_veo3
