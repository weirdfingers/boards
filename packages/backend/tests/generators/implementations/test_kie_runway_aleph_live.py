"""
Live API tests for KieRunwayAlephGenerator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_runway_aleph_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_runway_aleph_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import VideoArtifact
from boards.generators.implementations.kie.video.runway_aleph import (
    KieRunwayAlephGenerator,
    KieRunwayAlephInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


class TestKieRunwayAlephGeneratorLive:
    """Live API tests for KieRunwayAlephGenerator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieRunwayAlephGenerator()
        # Sync API keys from settings to os.environ for use in generator
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_video_to_video_basic(
        self, skip_if_no_kie_key, image_resolving_context, cost_logger
    ):
        """
        Test basic video-to-video generation.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal settings to reduce cost.
        """
        # Create test video artifact
        test_video = VideoArtifact(
            generation_id="test_input",
            storage_url="https://storage.googleapis.com/falserverless/kling/kling_output.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=None,
        )

        # Create minimal input to reduce cost
        inputs = KieRunwayAlephInput(
            prompt="make the scene slightly more cinematic",
            video_source=test_video,
            aspect_ratio="16:9",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp4"
        assert artifact.duration == 5.0
