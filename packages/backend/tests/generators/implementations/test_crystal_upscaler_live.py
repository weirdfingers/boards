"""
Live API tests for FalCrystalUpscalerGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_crystal_upscaler_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_crystal_upscaler_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.crystal_upscaler import (
    CrystalUpscalerInput,
    FalCrystalUpscalerGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestCrystalUpscalerGeneratorLive:
    """Live API tests for FalCrystalUpscalerGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalCrystalUpscalerGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic upscaling with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a small publicly accessible test image to minimize cost.
        """
        # Use a small publicly accessible test image (256x256 solid color from placeholder services)
        # This is a simple red square image that's small and cheap to process
        test_image_url = "https://placehold.co/256x256/ff0000/ff0000.png"

        # Create test image artifact
        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create minimal input to reduce cost (use default 2x scale)
        inputs = CrystalUpscalerInput(
            image_url=test_artifact,
            scale_factor=2,  # Minimal scale factor
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.width > 0
        assert artifact.height > 0
        # Output should be approximately 2x the input size (256 * 2 = 512)
        # Allow some tolerance for processing differences
        assert artifact.width >= 500
        assert artifact.height >= 500

    @pytest.mark.asyncio
    async def test_generate_with_higher_scale_factor(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test upscaling with a higher scale factor.

        Verifies that scale_factor parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/128x128/00ff00/00ff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input2",
            storage_url=test_image_url,
            format="png",
            width=128,
            height=128,
        )

        # Create input with 4x scale factor
        inputs = CrystalUpscalerInput(
            image_url=test_artifact,
            scale_factor=4,
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.width > 0
        assert artifact.height > 0

        # Output should be approximately 4x the input size (128 * 4 = 512)
        # Allow some tolerance for processing differences
        assert artifact.width >= 500
        assert artifact.height >= 500

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Create dummy input (artifact won't be used for estimation)
        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url="https://example.com/test.png",
            format="png",
            width=256,
            height=256,
        )

        # Test with default scale factor
        inputs_default = CrystalUpscalerInput(image_url=test_artifact)
        cost_default = await self.generator.estimate_cost(inputs_default)

        # Test with higher scale factor
        inputs_high = CrystalUpscalerInput(image_url=test_artifact, scale_factor=10)
        cost_high = await self.generator.estimate_cost(inputs_high)

        # Cost should be fixed regardless of scale factor
        assert cost_default == cost_high

        # Sanity check on absolute costs
        assert cost_default > 0.0
        assert cost_default < 0.2  # Should be under $0.20 per upscale (estimated at ~$0.05)

    @pytest.mark.asyncio
    async def test_generate_portrait_image(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test upscaling with a portrait-oriented test image.

        Since Crystal Upscaler is optimized for facial details, test with
        a portrait aspect ratio that's common for face photos.
        """
        # Use a portrait-oriented test image (256x384 = 2:3 aspect ratio)
        test_image_url = "https://placehold.co/256x384/0000ff/0000ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input3",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=384,
        )

        # Use minimal 2x scale to keep costs low
        inputs = CrystalUpscalerInput(
            image_url=test_artifact,
            scale_factor=2,
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")

        # Verify dimensions - should maintain aspect ratio and be ~2x larger
        assert artifact.width >= 500  # ~512px
        assert artifact.height >= 750  # ~768px
        # Verify portrait aspect ratio is maintained (height > width)
        assert artifact.height > artifact.width
