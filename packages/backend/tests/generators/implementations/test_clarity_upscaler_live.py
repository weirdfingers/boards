"""
Live API tests for FalClarityUpscalerGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_clarity_upscaler_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_clarity_upscaler_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.clarity_upscaler import (
    ClarityUpscalerInput,
    FalClarityUpscalerGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestClarityUpscalerGeneratorLive:
    """Live API tests for FalClarityUpscalerGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalClarityUpscalerGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic upscaling with minimal parameters.

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
        inputs = ClarityUpscalerInput(
            image_url=test_artifact,
            upscale_factor=2.0,  # 2x upscale (minimal)
            num_inference_steps=4,  # Minimum steps for speed
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
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "png"

        # Verify upscaling happened (output should be ~2x larger)
        # Allow some tolerance for API processing
        assert test_artifact.width is not None and test_artifact.height is not None
        expected_width = test_artifact.width * inputs.upscale_factor
        expected_height = test_artifact.height * inputs.upscale_factor
        assert abs(artifact.width - expected_width) < 50
        assert abs(artifact.height - expected_height) < 50

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test upscaling with custom creativity and resemblance parameters.

        Verifies that quality control parameters are correctly processed.
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

        # Create input with custom parameters
        inputs = ClarityUpscalerInput(
            image_url=test_artifact,
            upscale_factor=2.0,
            creativity=0.5,  # Higher creativity
            resemblance=0.8,  # Higher resemblance to original
            num_inference_steps=4,  # Minimal for speed
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
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0

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

        inputs = ClarityUpscalerInput(image_url=test_artifact)
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 0.2  # Sanity check - should be under $0.20

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
        inputs = ClarityUpscalerInput(
            image_url=test_artifact,
            upscale_factor=2.0,
            seed=42,  # Fixed seed
            num_inference_steps=4,  # Minimal for speed
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

    @pytest.mark.asyncio
    async def test_generate_4x_upscale(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test maximum upscale factor (4x).

        Verifies that the maximum upscale factor works correctly.
        """
        # Use small test image
        test_image_url = "https://placehold.co/128x128/ff00ff/ff00ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input4",
            storage_url=test_image_url,
            format="png",
            width=128,
            height=128,
        )

        # Create input with max upscale factor
        inputs = ClarityUpscalerInput(
            image_url=test_artifact,
            upscale_factor=4.0,  # Maximum upscale
            num_inference_steps=4,  # Minimal for speed
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

        # Verify upscaling to 4x (128 * 4 = 512)
        assert test_artifact.width is not None and test_artifact.height is not None
        assert artifact.width is not None and artifact.height is not None
        expected_width = test_artifact.width * 4
        expected_height = test_artifact.height * 4
        assert abs(artifact.width - expected_width) < 50
        assert abs(artifact.height - expected_height) < 50
