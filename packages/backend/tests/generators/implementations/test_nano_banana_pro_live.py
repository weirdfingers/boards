"""
Live API tests for FalNanoBananaProGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_nano_banana_pro_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_nano_banana_pro_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.nano_banana_pro import (
    FalNanoBananaProGenerator,
    NanoBananaProInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestNanoBananaProGeneratorLive:
    """Live API tests for FalNanoBananaProGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalNanoBananaProGenerator()
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
        estimated_cost = await self.generator.estimate_cost(NanoBananaProInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = NanoBananaProInput(
            prompt="A simple red circle on white background",
            aspect_ratio="1:1",  # Square, default
            num_images=1,  # Single image
            resolution="1K",  # Lowest resolution
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
        # Dimensions are optional, but if present should be valid
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format in ["jpeg", "png", "webp"]

    @pytest.mark.asyncio
    async def test_generate_with_different_aspect_ratio(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with different aspect ratio.

        Verifies that aspect_ratio parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            NanoBananaProInput(prompt="test", aspect_ratio="16:9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape aspect ratio
        inputs = NanoBananaProInput(
            prompt="Minimalist landscape with mountains",
            aspect_ratio="16:9",
            num_images=1,
            resolution="1K",
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
        # Dimensions are optional, but if present should be valid
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_batch(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test batch image generation.

        Verifies that multiple images can be generated in a single request.
        """
        # Create input with small batch (2 images to minimize cost)
        inputs = NanoBananaProInput(
            prompt="Simple geometric shapes",
            aspect_ratio="1:1",
            num_images=2,  # Test batch functionality
            resolution="1K",
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
            assert artifact.storage_url is not None
            # Dimensions are optional, but if present should be valid
            if artifact.width is not None:
                assert artifact.width > 0
            if artifact.height is not None:
                assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_batch_size(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with batch size.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Single image
        inputs_1 = NanoBananaProInput(prompt="test", num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Four images (max for nano-banana-pro)
        inputs_4 = NanoBananaProInput(prompt="test", num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.1  # Should be well under $0.10 per image
