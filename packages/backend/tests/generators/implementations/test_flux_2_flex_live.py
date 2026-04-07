"""
Live API tests for FalFlux2FlexGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_flux_2_flex_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_flux_2_flex_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.flux_2_flex import (
    FalFlux2FlexGenerator,
    Flux2FlexInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFlux2FlexGeneratorLive:
    """Live API tests for FalFlux2FlexGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalFlux2FlexGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic image generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal settings (single image) to reduce cost.
        """
        # Log estimated cost
        inputs = Flux2FlexInput(prompt="A simple red cube on a white background")
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "png"

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test image generation with custom parameters.

        Verifies that custom image size, format, and inference settings
        are correctly processed.
        """
        inputs = Flux2FlexInput(
            prompt="A serene mountain landscape at sunset with warm colors",
            image_size="landscape_16_9",
            output_format="jpeg",
            num_inference_steps=20,
            guidance_scale=5.0,
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "jpeg"

    @pytest.mark.asyncio
    async def test_estimate_cost_scales_with_num_images(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with number of images.

        This doesn't make an API call, just verifies the cost logic.
        """
        # 1 image
        inputs_1 = Flux2FlexInput(prompt="test", num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # 2 images
        inputs_2 = Flux2FlexInput(prompt="test", num_images=2)
        cost_2 = await self.generator.estimate_cost(inputs_2)

        # 4 images
        inputs_4 = Flux2FlexInput(prompt="test", num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with num_images
        assert cost_2 == cost_1 * 2
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 1.0  # Should be under $1.00 per image
