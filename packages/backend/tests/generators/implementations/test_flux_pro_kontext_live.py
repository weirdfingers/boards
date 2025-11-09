"""
Live API tests for FalFluxProKontextGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_flux_pro_kontext_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_flux_pro_kontext_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.flux_pro_kontext import (
    FalFluxProKontextGenerator,
    FluxProKontextInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFluxProKontextGeneratorLive:
    """Live API tests for FalFluxProKontextGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalFluxProKontextGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic image-to-image generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a small publicly accessible test image to minimize cost.
        """
        # Use a small publicly accessible test image (256x256 solid color from placeholder services)
        # This is a simple red square image that's small and cheap to process
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
        inputs = FluxProKontextInput(
            prompt="Add a small white circle in the center",
            image_url=test_artifact,
            num_images=1,  # Single image
            output_format="jpeg",  # JPEG is cheaper than PNG
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
        test_image_url = "https://placehold.co/256x256/00ff00/00ff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input2",
            storage_url=test_image_url,
            format="png",
            width=256,
            height=256,
        )

        # Create input with specific aspect ratio
        inputs = FluxProKontextInput(
            prompt="Make it blue",
            image_url=test_artifact,
            aspect_ratio="16:9",
            num_images=1,
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
        assert artifact.width > 0
        assert artifact.height > 0

        # 16:9 aspect ratio should have width > height
        # (though exact dimensions depend on the API's processing)
        assert artifact.width > artifact.height

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
        inputs_1 = FluxProKontextInput(prompt="test", image_url=test_artifact, num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Multiple images
        inputs_4 = FluxProKontextInput(prompt="test", image_url=test_artifact, num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 0.2  # Should be under $0.20 per image (estimated at ~$0.055)

    @pytest.mark.asyncio
    async def test_generate_with_seed(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
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

        # Create input with specific seed
        inputs = FluxProKontextInput(
            prompt="Add yellow stars",
            image_url=test_artifact,
            seed=42,  # Fixed seed
            num_images=1,
            output_format="jpeg",
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
