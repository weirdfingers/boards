"""
Live API tests for FalNanoBananaProEditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_nano_banana_pro_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_nano_banana_pro_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.nano_banana_pro_edit import (
    FalNanoBananaProEditGenerator,
    NanoBananaProEditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestNanoBananaProEditGeneratorLive:
    """Live API tests for FalNanoBananaProEditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalNanoBananaProEditGenerator()
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
        inputs = NanoBananaProEditInput(
            prompt="Add text 'HELLO' in the center",
            image_sources=[test_artifact],
            num_images=1,  # Single image
            resolution="1K",  # Lowest resolution
            output_format="jpeg",  # JPEG output
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
    async def test_generate_with_aspect_ratio(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with specific aspect ratio.

        Verifies that aspect_ratio parameter is correctly processed.
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

        # Create input with landscape aspect ratio
        inputs = NanoBananaProEditInput(
            prompt="Change the color to blue",
            image_sources=[test_artifact],
            aspect_ratio="16:9",  # Landscape aspect ratio
            num_images=1,
            resolution="1K",
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
        assert artifact.storage_url.startswith("https://")
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_multiple_inputs(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with multiple input images.

        Verifies that the generator can process multiple source images.
        """
        # Use small test images (different colors)
        test_artifact_1 = ImageArtifact(
            generation_id="test_input3a",
            storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
            format="png",
            width=256,
            height=256,
        )
        test_artifact_2 = ImageArtifact(
            generation_id="test_input3b",
            storage_url="https://placehold.co/256x256/0000ff/0000ff.png",
            format="png",
            width=256,
            height=256,
        )

        # Create input with multiple source images
        inputs = NanoBananaProEditInput(
            prompt="Blend these colors together",
            image_sources=[test_artifact_1, test_artifact_2],
            num_images=1,
            resolution="1K",
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
        assert artifact.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_batch(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test batch image generation.

        Verifies that multiple images can be generated in a single request.
        """
        # Use small test image
        test_artifact = ImageArtifact(
            generation_id="test_input4",
            storage_url="https://placehold.co/512x512/ffff00/ffff00.png",
            format="png",
            width=512,
            height=512,
        )

        # Create input with small batch (2 images to minimize cost)
        inputs = NanoBananaProEditInput(
            prompt="Add geometric shapes",
            image_sources=[test_artifact],
            num_images=2,  # Test batch functionality
            resolution="1K",
            output_format="jpeg",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify we got 2 images
        assert result.outputs is not None
        assert len(result.outputs) == 2

        # Verify both artifacts are valid
        for artifact in result.outputs:
            assert isinstance(artifact, ImageArtifact)
            assert artifact.storage_url is not None
            assert artifact.storage_url.startswith("https://")
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
        # Create dummy input (artifact won't be used for estimation)
        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url="https://example.com/test.png",
            format="png",
            width=512,
            height=512,
        )

        # Single image
        inputs_1 = NanoBananaProEditInput(
            prompt="test prompt", image_sources=[test_artifact], num_images=1
        )
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Four images (max for nano-banana-pro)
        inputs_4 = NanoBananaProEditInput(
            prompt="test prompt", image_sources=[test_artifact], num_images=4
        )
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.1  # Should be well under $0.10 per image
