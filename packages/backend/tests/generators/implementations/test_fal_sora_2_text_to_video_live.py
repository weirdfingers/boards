"""
Live API tests for FalSora2TextToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_fal_sora_2_text_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_fal_sora_2_text_to_video_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.fal_sora_2_text_to_video import (
    FalSora2TextToVideoGenerator,
    Sora2TextToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestSora2TextToVideoGeneratorLive:
    """Live API tests for FalSora2TextToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalSora2TextToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings (4-second duration) to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            Sora2TextToVideoInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Sora2TextToVideoInput(
            prompt="A simple rotating cube",
            duration=4,  # Shortest duration
            aspect_ratio="16:9",
            resolution="720p",
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
        assert artifact.width > 0
        assert artifact.height > 0
        assert artifact.format == "mp4"
        assert artifact.duration is not None
        assert artifact.duration >= 4.0  # Should be at least 4 seconds

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with custom parameters.

        Verifies that custom aspect_ratio and duration are correctly processed.
        """
        # Create input with custom parameters
        inputs = Sora2TextToVideoInput(
            prompt="A serene mountain landscape at sunset",
            duration=8,  # Medium duration to balance cost and testing
            aspect_ratio="9:16",  # Portrait mode
            resolution="720p",
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
        # For 9:16 portrait at 720p, expect 720x1280
        assert artifact.width > 0
        assert artifact.height > 0
        assert artifact.format == "mp4"
        assert artifact.duration is not None
        assert artifact.duration >= 8.0  # Should be at least 8 seconds

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_duration(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with duration.

        This doesn't make an API call, just verifies the cost logic.
        """
        # 4-second video
        inputs_4s = Sora2TextToVideoInput(prompt="test", duration=4)
        cost_4s = await self.generator.estimate_cost(inputs_4s)

        # 8-second video
        inputs_8s = Sora2TextToVideoInput(prompt="test", duration=8)
        cost_8s = await self.generator.estimate_cost(inputs_8s)

        # 12-second video
        inputs_12s = Sora2TextToVideoInput(prompt="test", duration=12)
        cost_12s = await self.generator.estimate_cost(inputs_12s)

        # Cost should scale linearly with duration
        assert cost_8s == cost_4s * 2
        assert cost_12s == cost_4s * 3

        # Sanity check on absolute costs
        assert cost_4s > 0.0
        assert cost_4s < 1.0  # Should be under $1.00 per 4-second video
