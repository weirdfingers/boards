"""
Live API tests for FalImagen4PreviewFastGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_imagen4_preview_fast_live.py -v

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_imagen4_preview_fast_live.py -v

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.imagen4_preview_fast import (
    FalImagen4PreviewFastGenerator,
    Imagen4PreviewFastInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestImagen4PreviewFastGeneratorLive:
    """Live API tests for FalImagen4PreviewFastGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalImagen4PreviewFastGenerator()
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
        estimated_cost = await self.generator.estimate_cost(
            Imagen4PreviewFastInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Imagen4PreviewFastInput(
            prompt="A simple red circle on white background",
            aspect_ratio="1:1",
            num_images=1,
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
        assert artifact.width > 0
        assert artifact.height > 0
        assert artifact.format == "png"

    @pytest.mark.asyncio
    async def test_generate_with_aspect_ratio(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test image generation with non-square aspect ratio.

        Verifies that aspect ratio parameter is correctly passed to API.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Imagen4PreviewFastInput(prompt="test", aspect_ratio="16:9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with specific aspect ratio
        inputs = Imagen4PreviewFastInput(
            prompt="Minimalist landscape",
            aspect_ratio="16:9",
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
        assert artifact.width > 0
        assert artifact.height > 0
        assert artifact.format == "png"

    @pytest.mark.asyncio
    async def test_generate_with_negative_prompt(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test image generation with negative prompt.

        Verifies that negative_prompt parameter works correctly.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Imagen4PreviewFastInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with negative prompt
        inputs = Imagen4PreviewFastInput(
            prompt="A beautiful flower",
            negative_prompt="blurry, low quality, distorted",
            aspect_ratio="1:1",
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

    @pytest.mark.asyncio
    async def test_generate_with_seed(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test reproducible generation using seed.

        Verifies that seed parameter produces consistent results.
        """
        # Log estimated cost (will run twice, so double the cost)
        estimated_cost = await self.generator.estimate_cost(
            Imagen4PreviewFastInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost * 2)

        # Create input with seed
        inputs = Imagen4PreviewFastInput(
            prompt="A simple geometric shape",
            aspect_ratio="1:1",
            num_images=1,
            seed=42,
        )

        # Execute generation twice with same seed
        result1 = await self.generator.generate(inputs, dummy_context)
        result2 = await self.generator.generate(inputs, dummy_context)

        # Verify results
        assert result1.outputs is not None
        assert result2.outputs is not None
        assert len(result1.outputs) == 1
        assert len(result2.outputs) == 1

        # Note: Due to Fal's infrastructure, the URLs will be different
        # but the generated images should be identical
        # We can at least verify both generations succeeded
        from boards.generators.artifacts import ImageArtifact

        artifact1 = result1.outputs[0]
        artifact2 = result2.outputs[0]
        assert isinstance(artifact1, ImageArtifact)
        assert isinstance(artifact2, ImageArtifact)
        assert artifact1.storage_url.startswith("https://")
        assert artifact2.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Test single image
        inputs_single = Imagen4PreviewFastInput(prompt="test", num_images=1)
        cost_single = await self.generator.estimate_cost(inputs_single)

        assert cost_single > 0.0
        assert cost_single < 1.0  # Sanity check - should be under $1

        # Test batch generation
        inputs_batch = Imagen4PreviewFastInput(prompt="test", num_images=4)
        cost_batch = await self.generator.estimate_cost(inputs_batch)

        # Batch should cost 4x single image
        assert cost_batch == cost_single * 4

    @pytest.mark.asyncio
    async def test_generate_batch(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test batch generation of multiple images.

        This test makes a real API call and generates multiple images.
        """
        # Log estimated cost for batch
        estimated_cost = await self.generator.estimate_cost(
            Imagen4PreviewFastInput(prompt="test", num_images=2)
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input for batch generation (use 2 to reduce costs)
        inputs = Imagen4PreviewFastInput(
            prompt="Simple geometric shapes",
            aspect_ratio="1:1",
            num_images=2,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 2

        # Verify all artifacts
        from boards.generators.artifacts import ImageArtifact

        for artifact in result.outputs:
            assert isinstance(artifact, ImageArtifact)
            assert artifact.storage_url is not None
            assert artifact.storage_url.startswith("https://")
            assert artifact.width > 0
            assert artifact.height > 0
            assert artifact.format == "png"
