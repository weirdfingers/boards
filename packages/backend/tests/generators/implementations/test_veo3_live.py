"""
Live API tests for FalVeo3Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_veo3_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_veo3_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.veo3 import (
    FalVeo3Generator,
    Veo3Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestVeo3GeneratorLive:
    """Live API tests for FalVeo3Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalVeo3Generator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(Veo3Input(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Veo3Input(
            prompt="A simple rotating sphere",
            duration="4s",  # Shortest duration
            resolution="720p",  # Lowest resolution
            aspect_ratio="1:1",  # Square format
            generate_audio=False,  # Save 50% cost by disabling audio
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 1

        # Verify artifact properties
        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "mp4"
        assert artifact.duration == 4

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with custom parameters.

        Verifies that custom parameters like seed and negative_prompt are correctly processed.
        """
        # Create input with custom parameters
        inputs = Veo3Input(
            prompt="A serene mountain landscape at sunset",
            duration="6s",
            aspect_ratio="16:9",
            resolution="720p",  # Use 720p to reduce cost
            generate_audio=False,  # Save 50% cost
            enhance_prompt=True,
            auto_fix=True,
            seed=42,
            negative_prompt="motion blur, shaky camera, low quality",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.width == 1280
        assert artifact.height == 720
        assert artifact.format == "mp4"
        assert artifact.duration == 6

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Test with audio enabled (full cost)
        inputs_with_audio = Veo3Input(prompt="test", generate_audio=True)
        cost_with_audio = await self.generator.estimate_cost(inputs_with_audio)

        # Test without audio (50% cost)
        inputs_without_audio = Veo3Input(prompt="test", generate_audio=False)
        cost_without_audio = await self.generator.estimate_cost(inputs_without_audio)

        # Without audio should be 50% of with audio
        assert cost_without_audio == cost_with_audio * 0.5

        # Verify estimates are in reasonable range
        assert cost_with_audio > 0.0
        assert cost_with_audio < 1.0  # Sanity check - should be well under $1.00
        assert cost_without_audio > 0.0
        assert cost_without_audio < 0.5
