"""
Live API tests for FalFlux2Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_flux_2_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_flux_2_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.flux_2 import (
    FalFlux2Generator,
    Flux2Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFlux2GeneratorLive:
    """Live API tests for FalFlux2Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalFlux2Generator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic image generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(Flux2Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Flux2Input(
            prompt="A simple red circle on white background",
            image_size="square",
            num_images=1,
            acceleration="high",  # Fastest/cheapest option
            num_inference_steps=4,  # Minimum steps
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 1

        # Verify artifact properties
        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        # Storage URLs should be valid HTTPS URLs
        assert artifact.storage_url.startswith("https://")
        # Dimensions should be positive if present
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "png"

    @pytest.mark.asyncio
    async def test_generate_with_landscape_aspect(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test image generation with landscape aspect ratio.

        Verifies that image_size parameter is correctly passed to API.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Flux2Input(prompt="test", image_size="landscape_16_9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape aspect ratio
        inputs = Flux2Input(
            prompt="Minimalist landscape",
            image_size="landscape_16_9",
            num_images=1,
            acceleration="high",
            num_inference_steps=4,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = Flux2Input(prompt="test")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # FLUX.2 [dev] typically costs around $0.055 per generation
        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 0.5  # Sanity check - should be well under $0.50

    @pytest.mark.asyncio
    async def test_batch_generation(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test batch generation of multiple images.

        This test creates 2 images to verify batch handling while minimizing costs.
        """
        # Log estimated cost
        inputs = Flux2Input(
            prompt="test",
            num_images=2,
        )
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Create input for batch generation
        inputs = Flux2Input(
            prompt="Abstract geometric shapes",
            image_size="square",
            num_images=2,
            acceleration="high",
            num_inference_steps=4,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 2

        # Verify each artifact
        from boards.generators.artifacts import ImageArtifact

        for artifact in result.outputs:
            assert isinstance(artifact, ImageArtifact)
            assert artifact.storage_url is not None
            assert artifact.storage_url.startswith("https://")
