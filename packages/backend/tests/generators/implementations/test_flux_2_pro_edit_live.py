"""
Live API tests for FalFlux2ProEditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_flux_2_pro_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_flux_2_pro_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.flux_2_pro_edit import (
    FalFlux2ProEditGenerator,
    Flux2ProEditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFlux2ProEditGeneratorLive:
    """Live API tests for FalFlux2ProEditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalFlux2ProEditGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic image editing with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a small publicly accessible test image to minimize cost.
        """
        # Use a small publicly accessible test image (256x256 solid color)
        test_image_url = "https://placehold.co/256x256/ff0000/ff0000.png"

        # Create test image artifact
        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create minimal input to reduce cost
        inputs = Flux2ProEditInput(
            prompt="Add a small white circle in the center",
            image_sources=[test_artifact],
            output_format="jpeg",  # JPEG is cheaper than PNG
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
        # Dimensions are optional, but if present should be valid
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "jpeg"

    @pytest.mark.asyncio
    async def test_generate_with_multiple_images(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with multiple input images.

        Verifies that multi-reference editing works with @ symbol references.
        """
        # Use small test images
        test_image_1 = ImageArtifact(
            generation_id="test_input1",
            storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
            format="png",
            width=256,
            height=256,
        )

        test_image_2 = ImageArtifact(
            generation_id="test_input2",
            storage_url="https://placehold.co/256x256/0000ff/0000ff.png",
            format="png",
            width=256,
            height=256,
        )

        # Create input with multiple images and explicit references
        inputs = Flux2ProEditInput(
            prompt="Blend @1 and @2 together",
            image_sources=[test_image_1, test_image_2],
            output_format="jpeg",
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
        assert artifact.storage_url is not None

    @pytest.mark.asyncio
    async def test_generate_with_image_size(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with specific image size preset.

        Verifies that image_size parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/00ff00/00ff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with specific image size
        inputs = Flux2ProEditInput(
            prompt="Make it more vibrant",
            image_sources=[test_artifact],
            image_size="square",
            output_format="jpeg",
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
        assert artifact.storage_url is not None

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

        inputs = Flux2ProEditInput(
            prompt="test",
            image_sources=[test_artifact],
        )
        cost = await self.generator.estimate_cost(inputs)

        # Sanity check on absolute costs
        # Base cost is $0.03 per megapixel
        assert cost > 0.0
        assert cost == 0.03  # Base cost for 1 MP

    @pytest.mark.asyncio
    async def test_generate_with_seed(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/ffff00/ffff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with specific seed
        inputs = Flux2ProEditInput(
            prompt="Add subtle texture",
            image_sources=[test_artifact],
            seed=42,  # Fixed seed
            output_format="jpeg",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url is not None
