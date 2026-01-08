"""
Live API tests for FalSeedreamV45TextToImageGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_seedream_v45_text_to_image_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_seedream_v45_text_to_image_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.seedream_v45_text_to_image import (
    FalSeedreamV45TextToImageGenerator,
    SeedreamV45TextToImageInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestSeedreamV45TextToImageGeneratorLive:
    """Live API tests for FalSeedreamV45TextToImageGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalSeedreamV45TextToImageGenerator()
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
        estimated_cost = await self.generator.estimate_cost(
            SeedreamV45TextToImageInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input
        inputs = SeedreamV45TextToImageInput(
            prompt="A simple red circle on white background",
            num_images=1,
        )

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
        assert artifact.storage_url.startswith("https://")
        assert artifact.format in ["jpeg", "png", "webp"]

    @pytest.mark.asyncio
    async def test_generate_with_image_size(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with specific image size preset.

        Verifies that image_size parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            SeedreamV45TextToImageInput(prompt="test", image_size="landscape_16_9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape size
        inputs = SeedreamV45TextToImageInput(
            prompt="A minimalist landscape with mountains",
            image_size="landscape_16_9",
            num_images=1,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_with_seed(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            SeedreamV45TextToImageInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with specific seed
        inputs = SeedreamV45TextToImageInput(
            prompt="Simple geometric pattern",
            seed=42,
            num_images=1,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) >= 1
        assert result.outputs[0].storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = SeedreamV45TextToImageInput(prompt="test")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Sanity check - should be well under $1
        assert estimated_cost == 0.03  # Current estimate for single image
