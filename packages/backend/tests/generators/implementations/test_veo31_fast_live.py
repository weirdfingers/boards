"""
Live API tests for FalVeo31FastGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_veo31_fast_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_veo31_fast_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.veo31_fast import (
    FalVeo31FastGenerator,
    Veo31FastInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestVeo31FastGeneratorLive:
    """Live API tests for FalVeo31FastGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalVeo31FastGenerator()
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
        estimated_cost = await self.generator.estimate_cost(Veo31FastInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Veo31FastInput(
            prompt="A simple rotating sphere",
            duration="4s",  # Shortest duration
            resolution="720p",  # Lowest resolution
            aspect_ratio="16:9",  # Standard landscape
            generate_audio=False,  # Save 33% cost by disabling audio
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
    async def test_generate_portrait(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test video generation with portrait aspect ratio.

        Verifies that 9:16 aspect ratio works correctly.
        """
        # Create input with portrait aspect ratio
        inputs = Veo31FastInput(
            prompt="A serene waterfall in a forest",
            duration="4s",
            aspect_ratio="9:16",
            resolution="720p",  # Use 720p to reduce cost
            generate_audio=False,  # Save 33% cost
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
        assert artifact.width == 720
        assert artifact.height == 1280
        assert artifact.format == "mp4"
        assert artifact.duration == 4

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Test with audio enabled (full cost)
        inputs_with_audio = Veo31FastInput(prompt="test", generate_audio=True)
        cost_with_audio = await self.generator.estimate_cost(inputs_with_audio)

        # Test without audio (33% discount)
        inputs_without_audio = Veo31FastInput(prompt="test", generate_audio=False)
        cost_without_audio = await self.generator.estimate_cost(inputs_without_audio)

        # Without audio should be 67% of with audio (33% discount)
        assert cost_without_audio == pytest.approx(cost_with_audio * 0.67, rel=0.01)

        # Verify estimates are in reasonable range
        assert cost_with_audio > 0.0
        assert cost_with_audio < 1.0  # Sanity check - should be well under $1.00
        assert cost_without_audio > 0.0
        assert cost_without_audio < 0.5
