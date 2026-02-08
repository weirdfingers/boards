"""
Live API tests for FalKolorsVirtualTryOnGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_kolors_virtual_try_on_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_kolors_virtual_try_on_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.kolors_virtual_try_on import (
    FalKolorsVirtualTryOnGenerator,
    KolorsVirtualTryOnInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestKolorsVirtualTryOnGeneratorLive:
    """Live API tests for FalKolorsVirtualTryOnGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKolorsVirtualTryOnGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, image_resolving_context, cost_logger):
        """
        Test basic virtual try-on generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses small publicly accessible test images to minimize cost.
        """
        # Use small test images
        # Human image - simple placeholder person silhouette
        test_human_url = (
            "https://storage.googleapis.com/falserverless/model_tests/leffa/person_image.jpg"
        )
        # Garment image - simple placeholder
        test_garment_url = (
            "https://storage.googleapis.com/falserverless/model_tests/leffa/tshirt_image.jpg"
        )

        # Create test artifacts
        human_artifact = ImageArtifact(
            generation_id="test_human",
            storage_url=test_human_url,
            format="png",
            width=384,
            height=512,
        )
        garment_artifact = ImageArtifact(
            generation_id="test_garment",
            storage_url=test_garment_url,
            format="png",
            width=256,
            height=256,
        )

        # Create minimal input
        inputs = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
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
        # Dimensions should be valid if present
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Create dummy artifacts (won't be used for estimation)
        human_artifact = ImageArtifact(
            generation_id="test_human",
            storage_url="https://example.com/human.png",
            format="png",
            width=384,
            height=512,
        )
        garment_artifact = ImageArtifact(
            generation_id="test_garment",
            storage_url="https://example.com/garment.png",
            format="png",
            width=256,
            height=256,
        )

        inputs = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
        )

        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is reasonable
        assert estimated_cost > 0.0
        assert estimated_cost < 0.5  # Sanity check - should be under $0.50 per generation
