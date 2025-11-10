"""
Live API tests for FalSora2ImageToVideoProGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_sora_2_image_to_video_pro_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_sora_2_image_to_video_pro_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is more expensive than image generation.
These tests use minimal settings (4s duration, 720p) to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.sora_2_image_to_video_pro import (
    FalSora2ImageToVideoProGenerator,
    Sora2ImageToVideoProInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for video generation testing."""
    # Use a small publicly accessible test image from placehold.co
    return ImageArtifact(
        generation_id="test_image",
        storage_url="https://placehold.co/256x256/3498db/ffffff.png?text=Sora+Test",
        format="png",
        width=256,
        height=256,
    )


class TestSora2ImageToVideoProGeneratorLive:
    """Live API tests for FalSora2ImageToVideoProGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalSora2ImageToVideoProGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic_4s_720p(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test basic video generation with minimal parameters (4s, 720p).

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 4 second duration and 720p resolution to minimize cost.
        """
        # Create minimal input to reduce cost
        inputs = Sora2ImageToVideoProInput(
            prompt="A simple gentle camera movement",
            image_url=test_image_artifact,
            resolution="720p",  # Lower resolution to reduce cost
            aspect_ratio="auto",
            duration=4,  # Shortest duration to reduce cost
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

        # Verify video has reasonable dimensions
        # For 720p, expect height ~720 or width ~1280
        assert artifact.height >= 256 or artifact.width >= 256

        # Verify duration is close to what we requested
        assert artifact.duration >= 3  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_estimate_cost_duration_scaling(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that cost estimation scales with duration.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Cost for 4s (base)
        inputs_4s = Sora2ImageToVideoProInput(
            prompt="test",
            image_url=test_image_artifact,
            duration=4,
        )
        cost_4s = await self.generator.estimate_cost(inputs_4s)

        # Cost for 8s (should be 2x base)
        inputs_8s = Sora2ImageToVideoProInput(
            prompt="test",
            image_url=test_image_artifact,
            duration=8,
        )
        cost_8s = await self.generator.estimate_cost(inputs_8s)

        # Cost for 12s (should be 3x base)
        inputs_12s = Sora2ImageToVideoProInput(
            prompt="test",
            image_url=test_image_artifact,
            duration=12,
        )
        cost_12s = await self.generator.estimate_cost(inputs_12s)

        # Verify cost scaling
        assert cost_8s == cost_4s * 2
        assert cost_12s == cost_4s * 3

        # Sanity check on absolute costs
        assert cost_4s > 0.0
        assert cost_4s < 5.0  # Should be reasonable per video
        assert cost_12s < 10.0  # Even longest video should be under $10
