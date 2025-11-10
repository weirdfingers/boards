"""
Live API tests for FalQwenImageGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_qwen_image_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_qwen_image_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.qwen_image import (
    FalQwenImageGenerator,
    QwenImageInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestQwenImageGeneratorLive:
    """Live API tests for FalQwenImageGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalQwenImageGenerator()
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
        estimated_cost = await self.generator.estimate_cost(QwenImageInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = QwenImageInput(
            prompt="A simple red circle",
            image_size="square",  # Smaller size
            num_inference_steps=2,  # Minimum steps (range: 2-250)
            num_images=1,  # Single image
            use_turbo=True,  # Enable turbo for faster/cheaper generation
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
        assert artifact.format in ["jpeg", "png"]

    @pytest.mark.asyncio
    async def test_generate_with_text_rendering(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test Qwen-Image's advanced text rendering capabilities.

        Qwen-Image is known for exceptional text rendering, so we test with text in prompt.
        """
        # Create input with text to render in image
        inputs = QwenImageInput(
            prompt="A sign that says 'TEST' in bold letters",
            image_size="square",
            num_inference_steps=2,  # Minimum to reduce cost
            num_images=1,
            use_turbo=True,
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

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

    @pytest.mark.asyncio
    async def test_generate_batch(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test batch image generation.

        Verifies that multiple images can be generated in a single request.
        """
        # Create input with small batch (2 images to minimize cost)
        inputs = QwenImageInput(
            prompt="Simple geometric shapes",
            image_size="square",
            num_inference_steps=2,  # Minimum
            num_images=2,  # Test batch functionality
            use_turbo=True,
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
            assert artifact.storage_url.startswith("https://")
            assert artifact.width > 0
            assert artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_different_sizes(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with different image sizes.

        Verifies that image_size parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            QwenImageInput(prompt="test", image_size="landscape_16_9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape aspect ratio
        inputs = QwenImageInput(
            prompt="Minimalist landscape",
            image_size="landscape_16_9",
            num_inference_steps=2,
            num_images=1,
            use_turbo=True,
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

        # Landscape should have width > height (though exact dims depend on size preset)
        # We don't verify exact aspect ratio as API might vary

    @pytest.mark.asyncio
    async def test_generate_with_negative_prompt(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with negative prompt.

        Verifies that negative_prompt parameter is accepted.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(QwenImageInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with negative prompt
        inputs = QwenImageInput(
            prompt="A beautiful garden",
            negative_prompt="people, humans, faces",
            image_size="square",
            num_inference_steps=2,
            num_images=1,
            use_turbo=True,
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
    async def test_estimate_cost_matches_batch_size(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with batch size.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Single image
        inputs_1 = QwenImageInput(prompt="test", num_images=1)
        cost_1 = await self.generator.estimate_cost(inputs_1)

        # Four images (max for Qwen)
        inputs_4 = QwenImageInput(prompt="test", num_images=4)
        cost_4 = await self.generator.estimate_cost(inputs_4)

        # Cost should scale linearly with number of images
        assert cost_4 == cost_1 * 4

        # Sanity check on absolute costs
        assert cost_1 > 0.0
        assert cost_1 < 1.0  # Should be under $1.00 per image

    @pytest.mark.asyncio
    async def test_generate_with_seed(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(QwenImageInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with specific seed
        inputs = QwenImageInput(
            prompt="Simple pattern",
            image_size="square",
            num_inference_steps=2,
            seed=42,  # Fixed seed
            use_turbo=True,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_with_acceleration(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with acceleration settings.

        Verifies that acceleration parameter is accepted.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(QwenImageInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with high acceleration
        inputs = QwenImageInput(
            prompt="Quick test image",
            image_size="square",
            num_inference_steps=2,
            acceleration="high",  # Test acceleration
            use_turbo=True,
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
