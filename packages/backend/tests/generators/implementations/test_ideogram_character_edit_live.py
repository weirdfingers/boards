"""
Live API tests for FalIdeogramCharacterEditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_ideogram_character_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_ideogram_character_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.ideogram_character_edit import (
    FalIdeogramCharacterEditGenerator,
    IdeogramCharacterEditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestIdeogramCharacterEditGeneratorLive:
    """Live API tests for FalIdeogramCharacterEditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalIdeogramCharacterEditGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic character editing with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses small publicly accessible test images to minimize cost.
        """
        # Use small test images (256x256 solid colors from placeholder services)
        # In a real scenario, you'd use actual character images and masks
        test_image_url = "https://placehold.co/256x256/ff0000/ff0000.png"
        test_mask_url = "https://placehold.co/256x256/000000/ffffff.png"  # Black/white mask
        test_reference_url = "https://placehold.co/256x256/00ff00/00ff00.png"

        # Create test image artifacts
        test_image = ImageArtifact(
            generation_id="test_image",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        test_mask = ImageArtifact(
            generation_id="test_mask",
            storage_url=test_mask_url,
            format="png",
            width=256,
            height=256,
        )

        test_reference = ImageArtifact(
            generation_id="test_reference",
            storage_url=test_reference_url,
            format="png",
            width=256,
            height=256,
        )

        # Create minimal input to reduce cost
        inputs = IdeogramCharacterEditInput(
            prompt="Change character expression to happy",
            image_url=test_image,
            mask_url=test_mask,
            reference_image_urls=[test_reference],
            num_images=1,  # Single image to minimize cost
            rendering_speed="TURBO",  # Fastest/cheapest option
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
    async def test_generate_with_style(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with specific style parameter.

        Verifies that style parameter is correctly processed.
        """
        # Use small test images
        test_image_url = "https://placehold.co/256x256/0000ff/0000ff.png"
        test_mask_url = "https://placehold.co/256x256/ffffff/000000.png"
        test_reference_url = "https://placehold.co/256x256/ffff00/ffff00.png"

        test_image = ImageArtifact(
            generation_id="test_image2",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        test_mask = ImageArtifact(
            generation_id="test_mask2",
            storage_url=test_mask_url,
            format="png",
            width=256,
            height=256,
        )

        test_reference = ImageArtifact(
            generation_id="test_reference2",
            storage_url=test_reference_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with specific style
        inputs = IdeogramCharacterEditInput(
            prompt="Change character pose",
            image_url=test_image,
            mask_url=test_mask,
            reference_image_urls=[test_reference],
            style="REALISTIC",  # Specific style
            num_images=1,
            rendering_speed="TURBO",
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
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Create dummy artifacts (won't be used for estimation)
        test_image = ImageArtifact(
            generation_id="test_image",
            storage_url="https://example.com/image.png",
            format="png",
            width=256,
            height=256,
        )

        test_mask = ImageArtifact(
            generation_id="test_mask",
            storage_url="https://example.com/mask.png",
            format="png",
            width=256,
            height=256,
        )

        test_reference = ImageArtifact(
            generation_id="test_reference",
            storage_url="https://example.com/reference.png",
            format="png",
            width=256,
            height=256,
        )

        # Single image
        inputs_1 = IdeogramCharacterEditInput(
            prompt="test",
            image_url=test_image,
            mask_url=test_mask,
            reference_image_urls=[test_reference],
            num_images=1,
        )
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Multiple images
        inputs_4 = IdeogramCharacterEditInput(
            prompt="test",
            image_url=test_image,
            mask_url=test_mask,
            reference_image_urls=[test_reference],
            num_images=4,
        )
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.2  # Should be under $0.20 per image (estimated at $0.05)

    @pytest.mark.asyncio
    async def test_generate_with_seed(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Use small test images
        test_image_url = "https://placehold.co/256x256/ff00ff/ff00ff.png"
        test_mask_url = "https://placehold.co/256x256/000000/ffffff.png"
        test_reference_url = "https://placehold.co/256x256/00ffff/00ffff.png"

        test_image = ImageArtifact(
            generation_id="test_image3",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        test_mask = ImageArtifact(
            generation_id="test_mask3",
            storage_url=test_mask_url,
            format="png",
            width=256,
            height=256,
        )

        test_reference = ImageArtifact(
            generation_id="test_reference3",
            storage_url=test_reference_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with specific seed
        inputs = IdeogramCharacterEditInput(
            prompt="Change character clothing",
            image_url=test_image,
            mask_url=test_mask,
            reference_image_urls=[test_reference],
            seed=42,  # Fixed seed
            num_images=1,
            rendering_speed="TURBO",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url.startswith("https://")
