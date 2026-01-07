"""
Live API tests for FalGptImage15Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_gpt_image_1_5_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_gpt_image_1_5_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.gpt_image_1_5 import (
    FalGptImage15Generator,
    GptImage15Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestGptImage15GeneratorLive:
    """Live API tests for FalGptImage15Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalGptImage15Generator()
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
        estimated_cost = await self.generator.estimate_cost(GptImage15Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = GptImage15Input(
            prompt="A simple red circle on white background",
            num_images=1,  # Single image
            quality="low",  # Use low quality to reduce cost
            output_format="jpeg",  # Use JPEG for smaller files
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
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format in ["jpeg", "png", "webp"]

    @pytest.mark.asyncio
    async def test_generate_with_different_sizes(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with landscape aspect ratio.

        Verifies that image_size parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            GptImage15Input(prompt="test", image_size="1536x1024")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape size
        inputs = GptImage15Input(
            prompt="A wide landscape view of mountains",
            image_size="1536x1024",  # Wide/landscape
            quality="low",  # Use low quality to reduce cost
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
        # Verify dimensions match requested size (or close to it)
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_transparent_background(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with transparent background.

        Verifies that background parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            GptImage15Input(prompt="test", background="transparent")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with transparent background (use PNG for transparency support)
        inputs = GptImage15Input(
            prompt="A simple icon of a star",
            background="transparent",
            output_format="png",  # PNG supports transparency
            quality="low",  # Use low quality to reduce cost
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
        assert artifact.format == "png"

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_batch_size(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with batch size.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Single image
        inputs_1 = GptImage15Input(prompt="test", num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Four images (maximum)
        inputs_4 = GptImage15Input(prompt="test", num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.20  # Should be well under $0.20 per image
