"""
Live API tests for FalWan25PreviewTextToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_wan_25_preview_text_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_wan_25_preview_text_to_video_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.wan_25_preview_text_to_video import (
    FalWan25PreviewTextToVideoGenerator,
    Wan25PreviewTextToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestWan25PreviewTextToVideoGeneratorLive:
    """Live API tests for FalWan25PreviewTextToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalWan25PreviewTextToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings (5-second duration, 480p) to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Wan25PreviewTextToVideoInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Wan25PreviewTextToVideoInput(
            prompt="A simple rotating cube",
            duration=5,  # Shortest duration
            aspect_ratio="16:9",
            resolution="480p",  # Lowest resolution to reduce cost
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
        assert artifact.duration is not None
        assert artifact.duration >= 5.0  # Should be at least 5 seconds

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with custom parameters.

        Verifies that custom aspect_ratio and resolution are correctly processed.
        """
        # Create input with custom parameters
        inputs = Wan25PreviewTextToVideoInput(
            prompt="A serene mountain landscape at sunset",
            duration=5,  # Shortest duration to minimize cost
            aspect_ratio="9:16",  # Portrait mode
            resolution="480p",  # Lowest resolution to reduce cost
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
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "mp4"
        assert artifact.duration is not None
        assert artifact.duration >= 5.0  # Should be at least 5 seconds

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_duration(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with duration.

        This doesn't make an API call, just verifies the cost logic.
        """
        # 5-second video
        inputs_5s = Wan25PreviewTextToVideoInput(prompt="test", duration=5)
        cost_5s = await self.generator.estimate_cost(inputs_5s)

        # 10-second video
        inputs_10s = Wan25PreviewTextToVideoInput(prompt="test", duration=10)
        cost_10s = await self.generator.estimate_cost(inputs_10s)

        # Cost should scale linearly with duration
        assert cost_10s == cost_5s * 2

        # Sanity check on absolute costs
        assert cost_5s > 0.0
        assert cost_5s < 1.0  # Should be under $1.00 per 5-second video
