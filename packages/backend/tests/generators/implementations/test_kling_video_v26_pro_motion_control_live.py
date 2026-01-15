"""
Live API tests for FalKlingVideoV26ProMotionControlGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/
        test_kling_video_v26_pro_motion_control_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/
        test_kling_video_v26_pro_motion_control_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is more expensive than image generation.
These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.implementations.fal.video.kling_video_v26_pro_motion_control import (
    FalKlingVideoV26ProMotionControlGenerator,
    KlingVideoV26ProMotionControlInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for motion control testing.

    Uses a small publicly accessible test image.
    """
    return ImageArtifact(
        generation_id="test_image",
        storage_url="https://placehold.co/512x512/ff9900/ffffff.png",
        format="png",
        width=512,
        height=512,
    )


@pytest.fixture
def test_video_artifact():
    """Provide a sample video artifact for motion control testing.

    Note: This uses a public test video. For real tests, you'd need a video
    with a visible character performing motions.
    """
    # Using a short test video from a public source
    # This is a placeholder - actual tests would need a real motion video
    return VideoArtifact(
        generation_id="test_video",
        storage_url="https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
        format="mp4",
        width=640,
        height=360,
        duration=10.0,
        fps=24,
    )


class TestKlingVideoV26ProMotionControlGeneratorLive:
    """Live API tests for FalKlingVideoV26ProMotionControlGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKlingVideoV26ProMotionControlGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
        test_video_artifact,
    ):
        """
        Test basic motion control generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 'image' orientation for shorter output.
        """
        # Create minimal input to reduce cost
        inputs = KlingVideoV26ProMotionControlInput(
            image_url=test_image_artifact,
            video_url=test_video_artifact,
            character_orientation="image",  # Shorter duration limit
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
        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "mp4"

    @pytest.mark.asyncio
    async def test_generate_with_prompt(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
        test_video_artifact,
    ):
        """
        Test motion control generation with a text prompt.

        Verifies that custom prompt is correctly processed.
        """
        # Create input with prompt
        inputs = KlingVideoV26ProMotionControlInput(
            image_url=test_image_artifact,
            video_url=test_video_artifact,
            character_orientation="image",
            prompt="Apply dance movements smoothly",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_estimate_cost_is_reasonable(
        self, skip_if_no_fal_key, test_image_artifact, test_video_artifact
    ):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost logic.
        """
        inputs = KlingVideoV26ProMotionControlInput(
            image_url=test_image_artifact,
            video_url=test_video_artifact,
            character_orientation="image",
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1.00 per video
