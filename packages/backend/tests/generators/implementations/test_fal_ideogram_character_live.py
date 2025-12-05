"""
Live API tests for FalIdeogramCharacterGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_fal_ideogram_character_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_fal_ideogram_character_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.fal_ideogram_character import (
    FalIdeogramCharacterGenerator,
    IdeogramCharacterInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestIdeogramCharacterGeneratorLive:
    """Live API tests for FalIdeogramCharacterGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalIdeogramCharacterGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic character generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses TURBO speed and a small test image to minimize cost.
        """
        # Use a small publicly accessible test image (256x256 solid color)
        # This represents a simple character reference
        test_image_url = "https://placehold.co/256x256/ff0000/ff0000.png"

        # Create test character reference artifact
        test_artifact = ImageArtifact(
            generation_id="test_character_ref",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create minimal input to reduce cost
        inputs = IdeogramCharacterInput(
            prompt="Place the character in a sunny park",
            reference_image_urls=[test_artifact],
            rendering_speed="TURBO",  # Cheapest option ($0.10)
            num_images=1,  # Single image
            style="AUTO",
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
        assert artifact.format in ["png", "jpeg", "jpg", "webp"]

    @pytest.mark.asyncio
    async def test_generate_with_style(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with specific style preset.

        Verifies that the style parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/00ff00/00ff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_character_ref2",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with REALISTIC style
        inputs = IdeogramCharacterInput(
            prompt="The character standing in a coffee shop",
            reference_image_urls=[test_artifact],
            style="REALISTIC",
            rendering_speed="TURBO",  # Cheapest
            num_images=1,
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
        Test that cost estimation matches pricing tiers.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Create dummy input (artifact won't be used for estimation)
        test_artifact = ImageArtifact(
            generation_id="test_ref",
            storage_url="https://example.com/test.png",
            format="png",
            width=256,
            height=256,
        )

        # Test TURBO pricing ($0.10)
        inputs_turbo = IdeogramCharacterInput(
            prompt="test",
            reference_image_urls=[test_artifact],
            rendering_speed="TURBO",
            num_images=1,
        )
        cost_turbo = await self.generator.estimate_cost(inputs_turbo)
        assert cost_turbo == 0.10

        # Test BALANCED pricing ($0.15)
        inputs_balanced = IdeogramCharacterInput(
            prompt="test",
            reference_image_urls=[test_artifact],
            rendering_speed="BALANCED",
            num_images=1,
        )
        cost_balanced = await self.generator.estimate_cost(inputs_balanced)
        assert cost_balanced == 0.15

        # Test QUALITY pricing ($0.20)
        inputs_quality = IdeogramCharacterInput(
            prompt="test",
            reference_image_urls=[test_artifact],
            rendering_speed="QUALITY",
            num_images=1,
        )
        cost_quality = await self.generator.estimate_cost(inputs_quality)
        assert cost_quality == 0.20

        # Test multiple images (should scale linearly)
        inputs_multi = IdeogramCharacterInput(
            prompt="test",
            reference_image_urls=[test_artifact],
            rendering_speed="BALANCED",
            num_images=3,
        )
        cost_multi = await self.generator.estimate_cost(inputs_multi)
        assert cost_multi == 0.15 * 3  # $0.45

        # Sanity checks
        assert cost_turbo > 0.0
        assert cost_balanced > cost_turbo
        assert cost_quality > cost_balanced

    @pytest.mark.asyncio
    async def test_generate_multiple_images(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation of multiple images with same character.

        This verifies batch generation works correctly.
        NOTE: This test is more expensive due to multiple outputs.
        """
        # Use small test image
        test_image_url = "https://placehold.co/256x256/0000ff/0000ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_character_ref3",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input requesting 2 images with TURBO speed to reduce cost
        inputs = IdeogramCharacterInput(
            prompt="The character in different poses",
            reference_image_urls=[test_artifact],
            rendering_speed="TURBO",  # Cheapest option
            num_images=2,  # Request 2 images
            style="FICTION",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result structure - should have 2 outputs
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
