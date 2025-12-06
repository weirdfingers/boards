"""
Live API tests for FalFlux2ProGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_flux_2_pro_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_flux_2_pro_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.flux_2_pro import (
    FalFlux2ProGenerator,
    Flux2ProInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFlux2ProGeneratorLive:
    """Live API tests for FalFlux2ProGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalFlux2ProGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic image generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Create minimal input to reduce cost
        inputs = Flux2ProInput(
            prompt="A simple red circle on white background",
            image_size="square",  # Smallest preset (1 megapixel)
            output_format="jpeg",  # JPEG is more efficient
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        # Dimensions are optional, but if present should be valid
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "jpeg"

    @pytest.mark.asyncio
    async def test_generate_with_size_preset(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test image generation with specific size preset.

        Verifies that image_size parameter is correctly passed to API.
        """
        # Create input with specific image size
        inputs = Flux2ProInput(
            prompt="Minimalist landscape",
            image_size="landscape_16_9",
            output_format="jpeg",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        # Dimensions are optional, but if present should be valid
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0

        # 16:9 aspect ratio should have width > height
        if artifact.width is not None and artifact.height is not None:
            assert artifact.width > artifact.height

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Standard size (1 megapixel) = $0.03
        inputs_standard = Flux2ProInput(prompt="test", image_size="square")
        cost_standard = await self.generator.estimate_cost(inputs_standard)

        # HD square (~1.5 megapixels) = $0.03 + 0.5 * $0.015 = $0.0375
        inputs_hd = Flux2ProInput(prompt="test", image_size="square_hd")
        cost_hd = await self.generator.estimate_cost(inputs_hd)

        # Verify pricing matches documentation
        assert cost_standard == 0.03  # $0.03 for first megapixel
        assert cost_hd == pytest.approx(0.0375)  # $0.03 + 0.5 * $0.015

        # Sanity check on absolute costs
        assert cost_standard > 0.0
        assert cost_standard < 0.10  # Should be under $0.10 per image

    @pytest.mark.asyncio
    async def test_generate_with_seed(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Create input with specific seed
        inputs = Flux2ProInput(
            prompt="A blue triangle",
            image_size="square",
            seed=42,  # Fixed seed
            output_format="jpeg",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url is not None

    @pytest.mark.asyncio
    async def test_generate_png_format(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with PNG output format.

        Verifies that output_format parameter works correctly.
        """
        # Create input with PNG format
        inputs = Flux2ProInput(
            prompt="A green square",
            image_size="square",
            output_format="png",  # Lossless quality
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.format == "png"
        assert artifact.storage_url is not None
