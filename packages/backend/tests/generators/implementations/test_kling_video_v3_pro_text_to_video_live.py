"""
Live API tests for FalKlingVideoV3ProTextToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/\
        test_kling_video_v3_pro_text_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/\
        test_kling_video_v3_pro_text_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.kling_video_v3_pro_text_to_video import (
    FalKlingVideoV3ProTextToVideoGenerator,
    KlingVideoV3ProTextToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestKlingVideoV3ProTextToVideoGeneratorLive:
    """Live API tests for FalKlingVideoV3ProTextToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKlingVideoV3ProTextToVideoGenerator()
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
            KlingVideoV3ProTextToVideoInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = KlingVideoV3ProTextToVideoInput(
            prompt="A simple rotating cube",
            duration="5",  # Shortest duration
            aspect_ratio="1:1",  # Square format (smallest resolution)
            generate_audio=False,  # Skip audio to reduce cost
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
        assert artifact.format == "mp4"
        assert artifact.duration == 5.0
