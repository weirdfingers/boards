"""
Live API tests for FalLtx23TextToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_ltx_23_text_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_ltx_23_text_to_video_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.ltx_23_text_to_video import (
    FalLtx23TextToVideoGenerator,
    Ltx23TextToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestLtx23TextToVideoGeneratorLive:
    """Live API tests for FalLtx23TextToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalLtx23TextToVideoGenerator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses shortest duration and lowest resolution to reduce cost.
        """
        inputs = Ltx23TextToVideoInput(
            prompt="A simple rotating cube on a white background",
            duration=6,  # Shortest available duration
            resolution="1080p",  # Lowest available resolution
            aspect_ratio="16:9",
            fps=24,
            generate_audio=False,  # Skip audio to reduce cost/time
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, dummy_context)

        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "mp4"
        assert artifact.duration is not None
        assert artifact.duration > 0
