"""
Live API tests for FalReveEditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_reve_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_reve_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.reve_edit import (
    FalReveEditGenerator,
    ReveEditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestReveEditGeneratorLive:
    """Live API tests for FalReveEditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalReveEditGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic image editing with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a small publicly accessible test image to minimize cost.
        """
        # Use a small publicly accessible test image (512x512 solid color)
        # This is a simple red square image that's small and cheap to process
        test_image_url = "https://placehold.co/512x512/ff0000/ff0000.png"

        # Create test image artifact
        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create minimal input to reduce cost
        inputs = ReveEditInput(
            prompt="Add a simple white border",
            image_url=test_artifact,
            num_images=1,  # Single image
            output_format="jpeg",  # JPEG is smaller
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
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "jpeg"

    @pytest.mark.asyncio
    async def test_generate_with_multiple_outputs(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with multiple image outputs.

        Verifies that num_images parameter works correctly.
        """
        # Use small test image
        test_image_url = "https://placehold.co/512x512/00ff00/00ff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input2",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create input requesting 2 images
        inputs = ReveEditInput(
            prompt="Change color to blue",
            image_url=test_artifact,
            num_images=2,  # Multiple outputs
            output_format="jpeg",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result has 2 outputs
        assert result.outputs is not None
        assert len(result.outputs) == 2

        # Verify both artifacts
        for artifact in result.outputs:
            assert isinstance(artifact, ImageArtifact)
            assert artifact.storage_url.startswith("https://")
            if artifact.width is not None:
                assert artifact.width > 0
            if artifact.height is not None:
                assert artifact.height > 0
            assert artifact.format == "jpeg"

    @pytest.mark.asyncio
    async def test_generate_with_different_output_formats(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with different output formats.

        Verifies that output_format parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/512x512/0000ff/0000ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input3",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create input with webp output format
        inputs = ReveEditInput(
            prompt="Add texture",
            image_url=test_artifact,
            num_images=1,
            output_format="webp",
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
        assert artifact.format == "webp"

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
            width=512,
            height=512,
        )

        # Single image
        inputs_1 = ReveEditInput(prompt="test", image_url=test_artifact, num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Multiple images
        inputs_4 = ReveEditInput(prompt="test", image_url=test_artifact, num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs ($0.04 per image)
        assert cost_1 == 0.04
        assert cost_1 > 0.0
        assert cost_1 < 0.1  # Should be under $0.10 per image
