"""
Live API tests for FalKlingVideoV25TurboProTextToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_kling_video_v2_5_turbo_pro_text_to_video_live.py -v

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_kling_video_v2_5_turbo_pro_text_to_video_live.py -v

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
    KlingVideoV25TurboProTextToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestKlingVideoV25TurboProTextToVideoGeneratorLive:
    """Live API tests for FalKlingVideoV25TurboProTextToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKlingVideoV25TurboProTextToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings (5-second duration) to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            KlingVideoV25TurboProTextToVideoInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = KlingVideoV25TurboProTextToVideoInput(
            prompt="A simple rotating cube",
            duration="5",  # Shortest duration
            aspect_ratio="1:1",  # Square format (smallest resolution)
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
        # Dimensions are optional, but if present should be valid
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "mp4"
        assert artifact.duration == 5.0

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with custom parameters.

        Verifies that custom negative_prompt and cfg_scale are correctly processed.
        """
        # Create input with custom parameters
        inputs = KlingVideoV25TurboProTextToVideoInput(
            prompt="A serene mountain landscape at sunset",
            duration="5",  # Keep duration short to minimize cost
            aspect_ratio="16:9",
            negative_prompt="motion blur, shaky camera, low quality",
            cfg_scale=0.7,
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
        assert artifact.storage_url is not None
        assert artifact.width == 1920
        assert artifact.height == 1080
        assert artifact.format == "mp4"
        assert artifact.duration == 5.0

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_duration(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with duration.

        This doesn't make an API call, just verifies the cost logic.
        """
        # 5-second video
        inputs_5s = KlingVideoV25TurboProTextToVideoInput(prompt="test", duration="5")
        cost_5s = await self.generator.estimate_cost(inputs_5s)

        # 10-second video
        inputs_10s = KlingVideoV25TurboProTextToVideoInput(prompt="test", duration="10")
        cost_10s = await self.generator.estimate_cost(inputs_10s)

        # 10-second should cost 2x the 5-second
        assert cost_10s == cost_5s * 2

        # Sanity check on absolute costs
        assert cost_5s > 0.0
        assert cost_5s < 1.0  # Should be well under $1.00 per 5-second video
