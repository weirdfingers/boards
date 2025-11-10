"""
Live API tests for FalBytedanceSeedanceV1ProImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/\
test_fal_bytedance_seedance_v1_pro_image_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/\
test_fal_bytedance_seedance_v1_pro_image_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is expensive.
These tests use minimal settings (480p, 2 seconds) to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.fal_bytedance_seedance_v1_pro_image_to_video import (  # noqa: E501
    BytedanceSeedanceV1ProImageToVideoInput,
    FalBytedanceSeedanceV1ProImageToVideoGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for video generation testing."""
    # Use a small publicly accessible test image from placehold.co
    return ImageArtifact(
        generation_id="test_image",
        storage_url="https://placehold.co/256x256/00ff00/00ff00.png",
        format="png",
        width=256,
        height=256,
    )


class TestBytedanceSeedanceV1ProImageToVideoGeneratorLive:
    """Live API tests for FalBytedanceSeedanceV1ProImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalBytedanceSeedanceV1ProImageToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic_480p(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test basic video generation with minimal parameters (480p, 2 seconds).

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 480p resolution and 2-second duration to minimize cost.
        """
        # Create minimal input to reduce cost
        inputs = BytedanceSeedanceV1ProImageToVideoInput(
            prompt="simple motion",
            image=test_image_artifact,
            resolution="480p",  # Lowest resolution to reduce cost
            duration="2",  # Minimum duration to reduce cost
            aspect_ratio="auto",
            camera_fixed=True,  # Fixed camera might reduce processing
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

        # Verify expected dimensions for 480p
        assert artifact.height == 480 or artifact.width == 854

        # Verify expected duration
        assert artifact.duration == 2

    @pytest.mark.asyncio
    async def test_generate_with_end_image(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test video generation with end image for directional guidance.

        Uses minimal settings to reduce cost while testing the end_image feature.
        """
        # Create a different end image
        end_image = ImageArtifact(
            generation_id="test_end_image",
            storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
            format="png",
            width=256,
            height=256,
        )

        inputs = BytedanceSeedanceV1ProImageToVideoInput(
            prompt="smooth transition from green to red",
            image=test_image_artifact,
            end_image=end_image,
            resolution="480p",  # Lowest resolution
            duration="2",  # Minimum duration
            aspect_ratio="auto",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.duration == 2

    @pytest.mark.asyncio
    async def test_estimate_cost_scaling(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that cost estimation scales correctly with resolution and duration.

        This doesn't make an API call, just verifies the cost calculation logic.
        """
        # 480p, 2 seconds (cheapest)
        inputs_cheap = BytedanceSeedanceV1ProImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            resolution="480p",
            duration="2",
        )
        cost_cheap = await self.generator.estimate_cost(inputs_cheap)

        # 1080p, 5 seconds (more expensive)
        inputs_expensive = BytedanceSeedanceV1ProImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            resolution="1080p",
            duration="5",
        )
        cost_expensive = await self.generator.estimate_cost(inputs_expensive)

        # Verify cost scaling
        # 1080p has (1920*1080)/(854*480) = ~5.06x more pixels
        # 5 seconds is 2.5x more duration
        # Total should be ~12.65x more expensive
        assert cost_expensive > cost_cheap
        ratio = cost_expensive / cost_cheap
        assert ratio > 10  # Should be at least 10x more expensive

        # Sanity check on absolute costs
        assert cost_cheap > 0.0
        assert cost_cheap < 0.5  # 480p 2s should be relatively cheap
        assert cost_expensive > 0.0
        assert cost_expensive < 2.0  # 1080p 5s should still be under $2

    @pytest.mark.asyncio
    async def test_estimate_cost_resolution_impact(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that resolution has expected impact on cost (same duration).

        This verifies the cost formula accounts for pixel count correctly.
        """
        duration = "5"

        # 480p (854x480)
        inputs_480p = BytedanceSeedanceV1ProImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            resolution="480p",
            duration=duration,
        )
        cost_480p = await self.generator.estimate_cost(inputs_480p)

        # 720p (1280x720)
        inputs_720p = BytedanceSeedanceV1ProImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            resolution="720p",
            duration=duration,
        )
        cost_720p = await self.generator.estimate_cost(inputs_720p)

        # 1080p (1920x1080)
        inputs_1080p = BytedanceSeedanceV1ProImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            resolution="1080p",
            duration=duration,
        )
        cost_1080p = await self.generator.estimate_cost(inputs_1080p)

        # Verify costs increase with resolution
        assert cost_720p > cost_480p
        assert cost_1080p > cost_720p

        # Verify rough ratios based on pixel counts
        # 720p has (1280*720)/(854*480) = ~2.25x pixels vs 480p
        # 1080p has (1920*1080)/(1280*720) = ~2.25x pixels vs 720p
        ratio_720_to_480 = cost_720p / cost_480p
        ratio_1080_to_720 = cost_1080p / cost_720p

        # Allow some tolerance in ratios
        assert 2.0 < ratio_720_to_480 < 2.5
        assert 2.0 < ratio_1080_to_720 < 2.5
