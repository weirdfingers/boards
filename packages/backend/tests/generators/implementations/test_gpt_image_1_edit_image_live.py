"""
Live API tests for FalGptImage1EditImageGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_gpt_image_1_edit_image_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_gpt_image_1_edit_image_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.gpt_image_1_edit_image import (
    FalGptImage1EditImageGenerator,
    GptImage1EditImageInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestGptImage1EditImageGeneratorLive:
    """Live API tests for FalGptImage1EditImageGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalGptImage1EditImageGenerator()
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
        inputs = GptImage1EditImageInput(
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
        assert artifact.width > 0
        assert artifact.height > 0
        # GPT-Image-1 typically returns PNG
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
        inputs = GptImage1EditImageInput(
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
        assert artifact.width > 0
        assert artifact.height > 0

        # When image_size is 1024x1024, expect square output
        # (though exact dimensions depend on the API's processing)
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
        inputs = GptImage1EditImageInput(
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
        inputs = GptImage1EditImageInput(
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
            assert artifact.width > 0
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

        # Single image
        inputs_1 = GptImage1EditImageInput(prompt="test", image_urls=[test_artifact], num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Multiple images
        inputs_4 = GptImage1EditImageInput(prompt="test", image_urls=[test_artifact], num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.2  # Should be under $0.20 per image (estimated at ~$0.04)

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
        inputs = GptImage1EditImageInput(
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
