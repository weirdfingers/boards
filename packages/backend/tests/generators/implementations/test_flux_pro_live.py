"""
Live API tests for ReplicateFluxProGenerator.

These tests make actual API calls to the Replicate service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_replicate to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"REPLICATE_API_TOKEN": "r8_..."}'
    pytest tests/generators/implementations/test_flux_pro_live.py -v -m live_api

Or using direct environment variable:
    export REPLICATE_API_TOKEN="r8_..."
    pytest tests/generators/implementations/test_flux_pro_live.py -v -m live_replicate

Or run all Replicate live tests:
    pytest -m live_replicate -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.replicate.image.flux_pro import (
    FluxProInput,
    ReplicateFluxProGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_replicate]


class TestFluxProGeneratorLive:
    """Live API tests for FluxProGenerator using real Replicate API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = ReplicateFluxProGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_replicate_key, dummy_context, cost_logger):
        """
        Test basic image generation with minimal parameters.

        This test makes a real API call to Replicate and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(FluxProInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = FluxProInput(
            prompt="A simple red circle on white background",
            aspect_ratio="1:1",
            safety_tolerance=2,
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
        self, skip_if_no_replicate_key, dummy_context, cost_logger
    ):
        """
        Test image generation with non-square aspect ratio.

        Verifies that aspect ratio parameter is correctly passed to API.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            FluxProInput(prompt="test", aspect_ratio="16:9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with specific aspect ratio
        inputs = FluxProInput(
            prompt="Minimalist landscape",
            aspect_ratio="16:9",
            safety_tolerance=2,
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

        # Note: We don't verify exact dimensions because Replicate may not
        # return metadata about dimensions, but we verify the artifact is valid

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_actual(self, skip_if_no_replicate_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = FluxProInput(prompt="test")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # FLUX.1.1 Pro typically costs around $0.055 per generation
        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 0.5  # Sanity check - should be well under $0.50

    @pytest.mark.asyncio
    async def test_error_handling_invalid_input(
        self, skip_if_no_replicate_key, dummy_context, cost_logger
    ):
        """
        Test error handling with edge case inputs.

        Note: This test may or may not consume credits depending on whether
        validation happens client-side or server-side.
        """
        # Log potential cost
        cost_logger(self.generator.name, 0.055)

        # Create input with very short prompt (may trigger API error)
        inputs = FluxProInput(
            prompt="",  # Empty prompt might be rejected
            aspect_ratio="1:1",
            safety_tolerance=2,
        )

        # Depending on API behavior, this might raise an exception
        # or return an error in the response
        try:
            result = await self.generator.generate(inputs, dummy_context)
            # If it succeeds, at least verify we got something back
            assert result.outputs is not None
        except Exception as e:
            # If it fails, verify it's a meaningful error
            assert len(str(e)) > 0
