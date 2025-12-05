"""
Live API tests for FalGemini25FlashImageGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_gemini_25_flash_image_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_gemini_25_flash_image_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.gemini_25_flash_image import (
    FalGemini25FlashImageGenerator,
    Gemini25FlashImageInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestGemini25FlashImageGeneratorLive:
    """Live API tests for FalGemini25FlashImageGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalGemini25FlashImageGenerator()
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
        estimated_cost = await self.generator.estimate_cost(Gemini25FlashImageInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Gemini25FlashImageInput(
            prompt="Simple geometric shapes",
            aspect_ratio="1:1",  # Square format
            num_images=1,  # Single image
            output_format="jpeg",  # JPEG is typically smaller
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
        assert artifact.format == "jpeg"

    @pytest.mark.asyncio
    async def test_generate_batch(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test batch image generation.

        Verifies that multiple images can be generated in a single request.
        """
        # Create input with small batch (2 images to minimize cost)
        inputs = Gemini25FlashImageInput(
            prompt="Simple geometric shapes",
            aspect_ratio="1:1",
            num_images=2,  # Test batch functionality
            output_format="jpeg",
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
            assert artifact.storage_url.startswith("https://")
            assert artifact.width is not None and artifact.width > 0
            assert artifact.height is not None and artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_different_aspect_ratios(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with different aspect ratios.

        Verifies that aspect_ratio parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Gemini25FlashImageInput(prompt="test", aspect_ratio="16:9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape aspect ratio
        inputs = Gemini25FlashImageInput(
            prompt="Minimalist landscape with horizon",
            aspect_ratio="16:9",
            num_images=1,
            output_format="jpeg",
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
        # Width should be greater than height for 16:9 landscape
        assert artifact.width is not None and artifact.height is not None
        assert artifact.width > artifact.height

    @pytest.mark.asyncio
    async def test_generate_with_webp_format(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with WebP output format.

        Verifies that different output formats are supported.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Gemini25FlashImageInput(prompt="test", output_format="webp")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with WebP format
        inputs = Gemini25FlashImageInput(
            prompt="Abstract geometric pattern",
            aspect_ratio="1:1",
            num_images=1,
            output_format="webp",
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
        assert artifact.format == "webp"

    @pytest.mark.asyncio
    async def test_generate_with_limit_generations(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with limit_generations parameter.

        Verifies that the experimental limit_generations flag is accepted.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Gemini25FlashImageInput(prompt="test", limit_generations=True)
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with limit_generations enabled
        inputs = Gemini25FlashImageInput(
            prompt="A single red circle",
            aspect_ratio="1:1",
            num_images=1,
            output_format="jpeg",
            limit_generations=True,  # Experimental flag
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (limit_generations doesn't affect output structure)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        Note: Pricing for this model is not documented, so we use a placeholder.
        """
        inputs = Gemini25FlashImageInput(prompt="test", num_images=1)
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is 0.00 (placeholder since pricing is unknown)
        assert estimated_cost == 0.00
        assert isinstance(estimated_cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_scales_with_batch(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with batch size.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Single image
        inputs_1 = Gemini25FlashImageInput(prompt="test", num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Four images
        inputs_4 = Gemini25FlashImageInput(prompt="test", num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4
