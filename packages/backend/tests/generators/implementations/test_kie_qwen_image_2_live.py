"""
Live API tests for KieQwenImage2Generator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_qwen_image_2_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_qwen_image_2_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.kie.image.qwen_image_2 import (
    KieQwenImage2Generator,
    QwenImage2Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


class TestKieQwenImage2GeneratorLive:
    """Live API tests for KieQwenImage2Generator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieQwenImage2Generator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_text_to_image(self, skip_if_no_kie_key, dummy_context, cost_logger):
        """
        Test basic text-to-image generation.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal settings to reduce cost.
        """
        inputs = QwenImage2Input(
            prompt="A simple red circle on a white background",
            image_size="1:1",
            output_format="png",
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, dummy_context)

        assert result.outputs is not None
        assert len(result.outputs) >= 1

        artifact = result.outputs[0]
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("http")

    @pytest.mark.asyncio
    async def test_generate_image_edit(
        self, skip_if_no_kie_key, image_resolving_context, cost_logger
    ):
        """
        Test image editing mode.

        This test makes a real API call to Kie.ai and will consume credits.
        """
        test_image = ImageArtifact(
            generation_id="test_input",
            storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
            format="png",
            width=256,
            height=256,
        )

        inputs = QwenImage2Input(
            prompt="Make it blue",
            image_sources=[test_image],
            image_size="1:1",
            output_format="png",
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, image_resolving_context)

        assert result.outputs is not None
        assert len(result.outputs) >= 1

        artifact = result.outputs[0]
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("http")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_kie_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = QwenImage2Input(prompt="test")

        estimated_cost = await self.generator.estimate_cost(inputs)

        assert estimated_cost > 0.0
        assert estimated_cost < 0.10
        assert estimated_cost == 0.03
