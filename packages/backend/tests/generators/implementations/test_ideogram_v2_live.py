"""
Live API tests for FalIdeogramV2Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_ideogram_v2_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_ideogram_v2_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.image.ideogram_v2 import (
    FalIdeogramV2Generator,
    IdeogramV2Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestIdeogramV2GeneratorLive:
    """Live API tests for FalIdeogramV2Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalIdeogramV2Generator()
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
        estimated_cost = await self.generator.estimate_cost(IdeogramV2Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input
        inputs = IdeogramV2Input(
            prompt="A simple red circle",
            aspect_ratio="1:1",  # Standard square
            style="auto",  # Default style
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format in ["jpeg", "png"]

    @pytest.mark.asyncio
    async def test_generate_with_typography(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with text in prompt (Ideogram V2's specialty).

        Verifies that typography-focused prompts are processed correctly.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            IdeogramV2Input(prompt='Logo with text "AI"')
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with text in the prompt
        inputs = IdeogramV2Input(
            prompt='Create a modern logo with the text "AI Studio"',
            aspect_ratio="1:1",
            style="design",  # Design style is good for logos
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_different_aspect_ratios(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with different aspect ratios.

        Verifies that aspect_ratio parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            IdeogramV2Input(prompt="test", aspect_ratio="16:9")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with landscape aspect ratio
        inputs = IdeogramV2Input(
            prompt="Minimalist landscape with mountains",
            aspect_ratio="16:9",
            style="realistic",
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0

    @pytest.mark.asyncio
    async def test_generate_with_different_styles(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with different visual styles.

        Verifies that style parameter is correctly processed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            IdeogramV2Input(prompt="test", style="anime")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with anime style
        inputs = IdeogramV2Input(
            prompt="A cute cat",
            aspect_ratio="1:1",
            style="anime",
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        from boards.generators.artifacts import ImageArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_with_negative_prompt(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with negative prompt.

        Verifies that negative_prompt parameter is accepted.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(IdeogramV2Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with negative prompt
        inputs = IdeogramV2Input(
            prompt="A beautiful sunset",
            negative_prompt="blurry, low quality, distorted",
            aspect_ratio="16:9",
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) >= 1
        assert result.outputs[0].storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_with_seed(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test generation with fixed seed for reproducibility.

        Note: This test verifies seed is accepted, but doesn't verify
        reproducibility (would require 2 API calls).
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(IdeogramV2Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with specific seed
        inputs = IdeogramV2Input(
            prompt="Simple geometric pattern",
            aspect_ratio="1:1",
            seed=42,  # Fixed seed
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (seed doesn't affect output structure, just determinism)
        assert result.outputs is not None
        assert len(result.outputs) >= 1
        assert result.outputs[0].storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_generate_without_expand_prompt(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test generation with expand_prompt disabled.

        Verifies that MagicPrompt can be disabled.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(IdeogramV2Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create input with expand_prompt disabled
        inputs = IdeogramV2Input(
            prompt="A red square",
            expand_prompt=False,  # Disable MagicPrompt
            aspect_ratio="1:1",
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) >= 1
        assert result.outputs[0].storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = IdeogramV2Input(prompt="test")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Sanity check - should be well under $1
        assert estimated_cost == 0.04  # Current estimate
