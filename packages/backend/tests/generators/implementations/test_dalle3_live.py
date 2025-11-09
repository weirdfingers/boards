"""
Live API tests for OpenAIDallE3Generator.

These tests make actual API calls to the OpenAI service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_openai to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"OPENAI_API_KEY": "sk-..."}'
    pytest tests/generators/implementations/test_dalle3_live.py -v

Or using direct environment variable:
    export OPENAI_API_KEY="sk-..."
    pytest tests/generators/implementations/test_dalle3_live.py -v

Or run all OpenAI live tests:
    pytest -m live_openai -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.openai.image.dalle3 import (
    DallE3Input,
    OpenAIDallE3Generator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_openai]


class TestDallE3GeneratorLive:
    """Live API tests for OpenAIDallE3Generator using real OpenAI API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = OpenAIDallE3Generator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_openai_key, dummy_context, cost_logger):
        """
        Test basic image generation with minimal parameters.

        This test makes a real API call to OpenAI and will consume credits.
        Uses minimal/cheap settings to reduce cost (standard quality, square size).
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(DallE3Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = DallE3Input(
            prompt="A simple red circle on white background",
            size="1024x1024",  # Square size
            quality="standard",  # Cheaper than HD
            style="natural",
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
        assert artifact.width == 1024
        assert artifact.height == 1024
        assert artifact.format == "png"

    @pytest.mark.asyncio
    async def test_generate_landscape(self, skip_if_no_openai_key, dummy_context, cost_logger):
        """
        Test image generation with landscape aspect ratio.

        Verifies that non-square sizes work correctly.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            DallE3Input(prompt="test", size="1792x1024", quality="standard")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create landscape input
        inputs = DallE3Input(
            prompt="Minimalist landscape",
            size="1792x1024",  # Landscape
            quality="standard",
            style="natural",
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
        assert artifact.width == 1792
        assert artifact.height == 1024
        assert artifact.format == "png"

    @pytest.mark.asyncio
    async def test_estimate_cost_standard_vs_hd(self, skip_if_no_openai_key):
        """
        Test that cost estimation differentiates between standard and HD quality.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Standard quality
        inputs_standard = DallE3Input(prompt="test", quality="standard", size="1024x1024")
        cost_standard = await self.generator.estimate_cost(inputs_standard)

        # HD quality
        inputs_hd = DallE3Input(prompt="test", quality="hd", size="1024x1024")
        cost_hd = await self.generator.estimate_cost(inputs_hd)

        # HD should cost more than standard
        assert cost_hd >= cost_standard

        # Sanity check on absolute costs
        assert 0.03 < cost_standard < 0.10
        assert 0.03 < cost_hd < 0.20

    @pytest.mark.asyncio
    async def test_generate_vivid_style(self, skip_if_no_openai_key, dummy_context, cost_logger):
        """
        Test generation with vivid style.

        Verifies that style parameter is correctly passed.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            DallE3Input(prompt="test", style="vivid")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input with vivid style
        inputs = DallE3Input(
            prompt="Colorful abstract pattern",
            size="1024x1024",
            quality="standard",
            style="vivid",  # More saturated/dramatic colors
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result (style doesn't affect output structure)
        assert result.outputs is not None
        assert len(result.outputs) == 1
        assert result.outputs[0].storage_url.startswith("https://")
