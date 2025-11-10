"""
Live API tests for FalSora2ImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_sora2_image_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_sora2_image_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Sora 2 video generation is expensive. These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.sora2_image_to_video import (
    FalSora2ImageToVideoGenerator,
    Sora2ImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for video generation testing."""
    # Use small publicly accessible test image from placehold.co
    image = ImageArtifact(
        generation_id="test_image",
        storage_url="https://placehold.co/256x256/00ff00/00ff00.png",
        format="png",
        width=256,
        height=256,
    )
    return image


class TestSora2ImageToVideoGeneratorLive:
    """Live API tests for FalSora2ImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalSora2ImageToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic_4s(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test basic video generation with minimal parameters (4s, auto resolution).

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 4-second duration and auto resolution to minimize cost.
        """
        # Create minimal input to reduce cost
        inputs = Sora2ImageToVideoInput(
            prompt="simple smooth motion",
            image_url=test_image_artifact,
            duration=4,  # Shortest duration to reduce cost
            resolution="auto",
            aspect_ratio="auto",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

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
        assert artifact.duration is not None and artifact.duration > 0
        assert artifact.format == "mp4"

    @pytest.mark.asyncio
    async def test_estimate_cost_scales_with_duration(
        self, skip_if_no_fal_key, test_image_artifact
    ):
        """
        Test that cost estimation scales with duration.

        This doesn't make an API call, just verifies the cost estimation logic.
        """
        # Cost for 4s (base)
        inputs_4s = Sora2ImageToVideoInput(
            prompt="test",
            image_url=test_image_artifact,
            duration=4,
        )
        cost_4s = await self.generator.estimate_cost(inputs_4s)

        # Cost for 8s (should be 2x)
        inputs_8s = Sora2ImageToVideoInput(
            prompt="test",
            image_url=test_image_artifact,
            duration=8,
        )
        cost_8s = await self.generator.estimate_cost(inputs_8s)

        # Cost for 12s (should be 3x)
        inputs_12s = Sora2ImageToVideoInput(
            prompt="test",
            image_url=test_image_artifact,
            duration=12,
        )
        cost_12s = await self.generator.estimate_cost(inputs_12s)

        # Verify scaling
        assert cost_8s == cost_4s * 2.0
        assert cost_12s == cost_4s * 3.0

        # Sanity check on absolute costs
        assert cost_4s > 0.0
        assert cost_12s < 2.0  # Should be under $2 per video
