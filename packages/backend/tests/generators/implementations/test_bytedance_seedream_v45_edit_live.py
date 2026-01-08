"""
Live API tests for FalBytedanceSeedreamV45EditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_bytedance_seedream_v45_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_bytedance_seedream_v45_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.bytedance_seedream_v45_edit import (
    BytedanceSeedreamV45EditInput,
    FalBytedanceSeedreamV45EditGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestBytedanceSeedreamV45EditGeneratorLive:
    """Live API tests for FalBytedanceSeedreamV45EditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalBytedanceSeedreamV45EditGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.fixture
    def test_image_artifact(self):
        """Provide a sample image artifact for testing."""
        return ImageArtifact(
            generation_id="test_input",
            storage_url="https://placehold.co/512x512/ff0000/ff0000.png",
            format="png",
            width=512,
            height=512,
        )

    @pytest.mark.asyncio
    async def test_generate_basic(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger, test_image_artifact
    ):
        """
        Test basic image editing with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Create minimal input to reduce cost
        inputs = BytedanceSeedreamV45EditInput(
            prompt="Add a blue border around the image",
            image_sources=[test_image_artifact],
            num_images=1,  # Minimum images
            image_size="square",  # Standard size
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
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        # Storage URLs can be HTTPS URLs or other formats (data:, etc.)
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_seed(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger, test_image_artifact
    ):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        inputs = BytedanceSeedreamV45EditInput(
            prompt="Make the image brighter",
            image_sources=[test_image_artifact],
            num_images=1,
            seed=42,  # Fixed seed
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) >= 1
        assert result.outputs[0].storage_url is not None

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Single image
        inputs_1 = BytedanceSeedreamV45EditInput(
            prompt="test",
            image_sources=[test_image_artifact],
            num_images=1,
        )
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Multiple images
        inputs_3 = BytedanceSeedreamV45EditInput(
            prompt="test",
            image_sources=[test_image_artifact],
            num_images=3,
        )
        cost_3 = await self.generator.estimate_cost(inputs_3)

        # Verify estimate is in reasonable range
        assert cost_1 > 0.0
        assert cost_1 < 1.0  # Sanity check

        # Cost should scale linearly with number of images
        assert cost_3 == cost_1 * 3
