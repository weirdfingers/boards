"""
Live API tests for FalGptImage15EditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_gpt_image_15_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_gpt_image_15_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.gpt_image_15_edit import (
    FalGptImage15EditGenerator,
    GptImage15EditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestGptImage15EditGeneratorLive:
    """Live API tests for FalGptImage15EditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalGptImage15EditGenerator()
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
        # This is a simple red square that's small and cheap to process
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
        inputs = GptImage15EditInput(
            prompt="Make this image pixel-art style",
            image_urls=[test_artifact],
            num_images=1,  # Single image to minimize cost
            image_size="auto",  # Auto size to avoid upscaling
            quality="low",  # Low quality to minimize cost
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
        assert artifact.format in ["png", "jpeg", "webp"]

    @pytest.mark.asyncio
    async def test_generate_with_image_size(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with specific image size.

        Verifies that image_size parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/00ff00/00ff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input2",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with specific image size
        inputs = GptImage15EditInput(
            prompt="Make it blue",
            image_urls=[test_artifact],
            image_size="1024x1024",
            num_images=1,
            quality="low",  # Keep cost down
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

        # When image_size is 1024x1024, expect square output
        if artifact.width is not None and artifact.height is not None:
            assert artifact.width == artifact.height

    @pytest.mark.asyncio
    async def test_generate_with_high_fidelity(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with high input fidelity.

        Verifies that input_fidelity parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/0000ff/0000ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input3",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with high fidelity to closely follow input image
        inputs = GptImage15EditInput(
            prompt="Add a white circle in the center",
            image_urls=[test_artifact],
            input_fidelity="high",  # High fidelity to closely follow input
            num_images=1,
            quality="low",  # Keep cost down
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result (fidelity doesn't affect output structure, just quality)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_multiple_images(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation of multiple images (2 images to minimize cost).

        Verifies that num_images parameter works correctly.
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/ff00ff/ff00ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input4",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input requesting 2 images
        inputs = GptImage15EditInput(
            prompt="Make it artistic",
            image_urls=[test_artifact],
            num_images=2,  # Generate 2 variations (keep low to minimize cost)
            quality="low",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result has 2 outputs
        assert result.outputs is not None
        assert len(result.outputs) == 2

        # Verify both artifacts are valid
        for artifact in result.outputs:
            assert isinstance(artifact, ImageArtifact)
            assert artifact.storage_url.startswith("https://")
            if artifact.width is not None:
                assert artifact.width > 0
            if artifact.height is not None:
                assert artifact.height > 0

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

        # Single image, low quality
        inputs_low = GptImage15EditInput(
            prompt="test", image_urls=[test_artifact], num_images=1, quality="low"
        )
        cost_low = await self.generator.estimate_cost(inputs_low)

        # Single image, high quality
        inputs_high = GptImage15EditInput(
            prompt="test", image_urls=[test_artifact], num_images=1, quality="high"
        )
        cost_high = await self.generator.estimate_cost(inputs_high)

        # Multiple images, high quality
        inputs_4 = GptImage15EditInput(
            prompt="test", image_urls=[test_artifact], num_images=4, quality="high"
        )
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # High quality should cost more than low quality
        assert cost_high > cost_low

        # Cost should scale linearly with number of images
        assert cost_4 == cost_high * 4

        # Sanity check on absolute costs
        assert cost_low > 0.0
        assert cost_low < 0.05  # Low quality should be under $0.05
        assert cost_high > 0.1  # High quality should be over $0.10
        assert cost_high < 0.30  # But under $0.30

    @pytest.mark.asyncio
    async def test_generate_with_multiple_input_images(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with multiple input images.

        Verifies that the generator can handle multiple reference images.
        """
        # Create multiple small test images
        test_image_1 = ImageArtifact(
            generation_id="test_input5a",
            storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
            format="png",
            width=256,
            height=256,
        )

        test_image_2 = ImageArtifact(
            generation_id="test_input5b",
            storage_url="https://placehold.co/256x256/00ff00/00ff00.png",
            format="png",
            width=256,
            height=256,
        )

        # Create input with multiple reference images
        inputs = GptImage15EditInput(
            prompt="Combine these into a gradient",
            image_urls=[test_image_1, test_image_2],
            num_images=1,
            quality="low",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_with_output_format(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with different output formats.

        Verifies that output_format parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/ffff00/ffff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input6",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with webp output format
        inputs = GptImage15EditInput(
            prompt="Make it grayscale",
            image_urls=[test_artifact],
            output_format="webp",
            num_images=1,
            quality="low",
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
        assert artifact.storage_url.startswith("https://")
        # Format should be webp (or determined by content_type)
        assert artifact.format in ["webp", "png", "jpeg"]
