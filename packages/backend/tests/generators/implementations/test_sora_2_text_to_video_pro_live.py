"""
Live API tests for FalSora2TextToVideoProGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_sora_2_text_to_video_pro_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_sora_2_text_to_video_pro_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.sora_2_text_to_video_pro import (
    FalSora2TextToVideoProGenerator,
    Sora2TextToVideoProInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestSora2TextToVideoProGeneratorLive:
    """Live API tests for FalSora2TextToVideoProGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalSora2TextToVideoProGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings (4-second duration, 720p) to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(Sora2TextToVideoProInput(prompt="test"))
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = Sora2TextToVideoProInput(
            prompt="A simple rotating cube",
            duration=4,  # Shortest duration
            resolution="720p",  # Lower resolution to reduce cost
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
        assert artifact.duration >= 4.0  # At least 4 seconds

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with custom parameters.

        Verifies that custom resolution and aspect ratio are correctly processed.
        """
        # Create input with custom parameters
        inputs = Sora2TextToVideoProInput(
            prompt="A serene mountain landscape at sunset",
            duration=4,  # Keep duration short to minimize cost
            aspect_ratio="9:16",  # Portrait mode
            resolution="720p",  # Lower resolution
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
        # Portrait mode should have height > width
        assert artifact.height is not None and artifact.height > artifact.width
        assert artifact.format == "mp4"
        assert artifact.duration is not None
        assert artifact.duration >= 4.0

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_duration_and_resolution(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with duration and resolution.

        This doesn't make an API call, just verifies the cost logic.
        """
        # 4-second 720p video
        inputs_4s_720p = Sora2TextToVideoProInput(prompt="test", duration=4, resolution="720p")
        cost_4s_720p = await self.generator.estimate_cost(inputs_4s_720p)

        # 8-second 720p video
        inputs_8s_720p = Sora2TextToVideoProInput(prompt="test", duration=8, resolution="720p")
        cost_8s_720p = await self.generator.estimate_cost(inputs_8s_720p)

        # 8-second should cost 2x the 4-second
        assert cost_8s_720p == cost_4s_720p * 2

        # 4-second 1080p video
        inputs_4s_1080p = Sora2TextToVideoProInput(prompt="test", duration=4, resolution="1080p")
        cost_4s_1080p = await self.generator.estimate_cost(inputs_4s_1080p)

        # 1080p should cost more than 720p
        assert cost_4s_1080p > cost_4s_720p

        # Sanity check on absolute costs
        assert cost_4s_720p > 0.0
        assert cost_4s_720p < 1.0  # Should be well under $1.00 per 4-second video
        assert cost_4s_1080p < 2.0  # Should be well under $2.00 per 4-second 1080p video
