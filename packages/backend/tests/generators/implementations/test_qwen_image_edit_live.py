"""
Live API tests for FalQwenImageEditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_qwen_image_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_qwen_image_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.qwen_image_edit import (
    FalQwenImageEditGenerator,
    ImageSize,
    QwenImageEditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestQwenImageEditGeneratorLive:
    """Live API tests for FalQwenImageEditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalQwenImageEditGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic image editing with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a small publicly accessible test image to minimize cost.
        """
        # Use a small publicly accessible test image (512x512 solid color)
        # This is a simple red square image that's small and cheap to process
        test_image_url = "https://placehold.co/512x512/ff0000/ff0000.png"

        # Create test image artifact
        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create minimal input to reduce cost
        inputs = QwenImageEditInput(
            prompt="Add text 'HELLO'",
            image_url=test_artifact,
            num_images=1,  # Single image
            output_format="jpeg",  # JPEG is cheaper than PNG
            acceleration="high",  # Faster processing
            num_inference_steps=20,  # Fewer steps for faster/cheaper generation
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
    async def test_generate_with_preset_size(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with preset image size.

        Verifies that image_size preset parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/512x512/00ff00/00ff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input2",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create input with preset size
        inputs = QwenImageEditInput(
            prompt="Change to blue",
            image_url=test_artifact,
            image_size="square",  # Use preset size
            num_images=1,
            output_format="jpeg",
            acceleration="high",
            num_inference_steps=20,
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

    @pytest.mark.asyncio
    async def test_generate_with_custom_size(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with custom ImageSize object.

        Verifies that custom width/height parameters are correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/512x512/0000ff/0000ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input3",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create input with custom size
        custom_size = ImageSize(width=768, height=512)

        inputs = QwenImageEditInput(
            prompt="Add white border",
            image_url=test_artifact,
            image_size=custom_size,
            num_images=1,
            output_format="jpeg",
            acceleration="high",
            num_inference_steps=20,
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
        # Note: Output dimensions may not exactly match requested dimensions
        # depending on how the API processes the custom size
        assert artifact.width > 0
        assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_multiple_outputs(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with multiple image outputs.

        Verifies that num_images parameter works correctly.
        """
        # Use small test image
        test_image_url = "https://placehold.co/512x512/ffff00/ffff00.png"

        test_artifact = ImageArtifact(
            generation_id="test_input4",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create input requesting 2 images
        inputs = QwenImageEditInput(
            prompt="Add text 'TEST'",
            image_url=test_artifact,
            num_images=2,  # Multiple outputs
            output_format="jpeg",
            acceleration="high",
            num_inference_steps=20,
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result has 2 outputs
        assert result.outputs is not None
        assert len(result.outputs) == 2

        # Verify both artifacts
        for artifact in result.outputs:
            assert isinstance(artifact, ImageArtifact)
            assert artifact.storage_url.startswith("https://")
            assert artifact.width > 0
            assert artifact.height > 0
            assert artifact.format == "jpeg"

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
            width=512,
            height=512,
        )

        # Single image
        inputs_1 = QwenImageEditInput(prompt="test", image_url=test_artifact, num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Multiple images
        inputs_4 = QwenImageEditInput(prompt="test", image_url=test_artifact, num_images=4)
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
        # Use small test image
        test_image_url = "https://placehold.co/512x512/ff00ff/ff00ff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input5",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create input with specific seed
        inputs = QwenImageEditInput(
            prompt="Add grid pattern",
            image_url=test_artifact,
            seed=42,  # Fixed seed
            num_images=1,
            output_format="jpeg",
            acceleration="high",
            num_inference_steps=20,
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
    async def test_generate_with_guidance_scale(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with custom guidance scale.

        Verifies that guidance_scale parameter is correctly processed.
        """
        # Use small test image
        test_image_url = "https://placehold.co/512x512/00ffff/00ffff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input6",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        # Create input with higher guidance scale for stronger prompt adherence
        inputs = QwenImageEditInput(
            prompt="Replace with checkerboard pattern",
            image_url=test_artifact,
            guidance_scale=7.5,  # Higher than default 4.0
            num_images=1,
            output_format="jpeg",
            acceleration="high",
            num_inference_steps=20,
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url.startswith("https://")
