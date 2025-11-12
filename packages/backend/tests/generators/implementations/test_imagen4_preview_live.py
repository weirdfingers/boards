"""
Live API tests for FalImagen4PreviewGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_imagen4_preview_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_imagen4_preview_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.imagen4_preview import (
    FalImagen4PreviewGenerator,
    Imagen4PreviewInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestImagen4PreviewGeneratorLive:
    """Live API tests for FalImagen4PreviewGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalImagen4PreviewGenerator()
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
        estimated_cost = await self.generator.estimate_cost(Imagen4PreviewInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Imagen4PreviewInput(
            prompt="Simple geometric shapes",
            aspect_ratio="1:1",  # Square format
            resolution="1K",  # Lower resolution
            num_images=1,  # Single image
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
        assert artifact.width == 1024
        assert artifact.height == 1024
        assert artifact.format in ["jpeg", "png"]

    @pytest.mark.asyncio
    async def test_generate_batch(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test batch image generation.

        Verifies that multiple images can be generated in a single request.
        """
        # Create input with small batch (2 images to minimize cost)
        inputs = Imagen4PreviewInput(
            prompt="Simple geometric shapes",
            aspect_ratio="1:1",
            resolution="1K",
            num_images=2,  # Test batch functionality
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
    async def test_generate_with_different_aspect_ratios(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with different aspect ratios.

        Verifies that aspect_ratio parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Imagen4PreviewInput(prompt="test", aspect_ratio="16:9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape aspect ratio
        inputs = Imagen4PreviewInput(
            prompt="Minimalist landscape with horizon",
            aspect_ratio="16:9",
            resolution="1K",
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
        assert artifact.storage_url is not None
        assert artifact.width == 1024
        assert artifact.height == 576  # 16:9 ratio with 1K resolution

    @pytest.mark.asyncio
    async def test_generate_with_2k_resolution(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with 2K resolution.

        Verifies that resolution parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Imagen4PreviewInput(prompt="test", resolution="2K")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with 2K resolution
        inputs = Imagen4PreviewInput(
            prompt="High detail macro photography of a flower",
            aspect_ratio="1:1",
            resolution="2K",  # Higher resolution
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
        assert artifact.storage_url is not None
        assert artifact.width == 2048
        assert artifact.height == 2048

    @pytest.mark.asyncio
    async def test_generate_with_negative_prompt(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with negative prompt.

        Verifies that negative_prompt parameter is accepted.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(Imagen4PreviewInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with negative prompt
        inputs = Imagen4PreviewInput(
            prompt="A realistic photo of a cat",
            negative_prompt="cartoon, anime, illustration",
            aspect_ratio="1:1",
            resolution="1K",
            num_images=1,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (negative prompt doesn't affect output structure)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url is not None

    @pytest.mark.asyncio
    async def test_generate_with_seed(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(Imagen4PreviewInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with specific seed
        inputs = Imagen4PreviewInput(
            prompt="Abstract geometric pattern",
            aspect_ratio="1:1",
            resolution="1K",
            seed=42,  # Fixed seed
            num_images=1,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url is not None

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = Imagen4PreviewInput(prompt="test", num_images=1)
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is $0.04 per image
        assert estimated_cost == 0.04

        # Test batch cost scaling
        inputs_batch = Imagen4PreviewInput(prompt="test", num_images=4)
        estimated_cost_batch = await self.generator.estimate_cost(inputs_batch)
        assert estimated_cost_batch == 0.16  # 4 * $0.04

    @pytest.mark.asyncio
    async def test_estimate_cost_scales_with_batch(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with batch size.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Single image
        inputs_1 = Imagen4PreviewInput(prompt="test", num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Four images
        inputs_4 = Imagen4PreviewInput(prompt="test", num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.1  # Should be well under $0.10 per image
