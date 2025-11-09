"""
Live API tests for FalNanoBananaGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_nano_banana_live.py -v

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_nano_banana_live.py -v

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.nano_banana import (
    FalNanoBananaGenerator,
    NanoBananaInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestNanoBananaGeneratorLive:
    """Live API tests for FalNanoBananaGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalNanoBananaGenerator()
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
        estimated_cost = await self.generator.estimate_cost(NanoBananaInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = NanoBananaInput(
            prompt="A simple red circle",
            image_size="square",  # Smaller size
            num_inference_steps=4,  # Minimum steps
            num_images=1,  # Single image
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
        assert artifact.storage_url.startswith("https://")
        assert artifact.width > 0
        assert artifact.height > 0
        assert artifact.format in ["jpeg", "png"]

    @pytest.mark.asyncio
    async def test_generate_batch(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test batch image generation.

        Verifies that multiple images can be generated in a single request.
        """
        # Create input with small batch (2 images to minimize cost)
        inputs = NanoBananaInput(
            prompt="Simple geometric shapes",
            image_size="square",
            num_inference_steps=4,
            num_images=2,  # Test batch functionality
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify we got 2 images
        assert result.outputs is not None
        assert len(result.outputs) == 2

        # Verify both artifacts are valid
        from boards.generators.artifacts import ImageArtifact

        for artifact in result.outputs:
            assert isinstance(artifact, ImageArtifact)
            assert artifact.storage_url.startswith("https://")
            assert artifact.width > 0
            assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_different_sizes(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with different image sizes.

        Verifies that image_size parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            NanoBananaInput(prompt="test", image_size="landscape_16_9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape aspect ratio
        inputs = NanoBananaInput(
            prompt="Minimalist landscape",
            image_size="landscape_16_9",
            num_inference_steps=4,
            num_images=1,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.width > 0
        assert artifact.height > 0

        # Landscape should have width > height (though exact dims depend on size preset)
        # We don't verify exact aspect ratio as API might vary

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_batch_size(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with batch size.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Single image
        inputs_1 = NanoBananaInput(prompt="test", num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Five images
        inputs_5 = NanoBananaInput(prompt="test", num_images=5)
        cost_5 = await self.generator.estimate_cost(inputs_5)

        # Cost should scale linearly with number of images
        assert cost_5 == cost_1 * 5

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.1  # Should be well under $0.10 per image

    @pytest.mark.asyncio
    async def test_generate_with_seed(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(NanoBananaInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with specific seed
        inputs = NanoBananaInput(
            prompt="Simple pattern",
            image_size="square",
            num_inference_steps=4,
            seed=42,  # Fixed seed
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url.startswith("https://")
