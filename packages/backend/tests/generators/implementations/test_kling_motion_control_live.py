"""
Live API tests for FalKlingMotionControlGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_kling_motion_control_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_kling_motion_control_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation with motion control is more expensive than basic video generation.
These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.implementations.fal.video.kling_motion_control import (
    FalKlingMotionControlGenerator,
    KlingMotionControlInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for motion control testing.

    Using a person-like image for better motion control results.
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
    """Provide a sample video artifact for motion reference.

    Using a short sample video for motion control.
    Note: For live tests, this should be a real video URL with motion data.
    Using a placeholder for now - replace with actual test video URL.
    """
    # This is a placeholder - in real tests, use an actual short video
    # with clear human motion (e.g., a short dance clip)
    return VideoArtifact(
        generation_id="test_video",
        # Using a sample video from a public source
        storage_url="https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
        format="mp4",
        width=1280,
        height=720,
        duration=5.0,
        fps=25.0,
    )


class TestKlingMotionControlGeneratorLive:
    """Live API tests for FalKlingMotionControlGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKlingMotionControlGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic_image_mode(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
        test_video_artifact,
    ):
        """
        Test basic motion control generation with image orientation mode.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses image mode (up to 10s) for shorter, cheaper generation.
        """
        # Create minimal input to reduce cost
        inputs = KlingMotionControlInput(
            image_url=test_image_artifact,
            video_url=test_video_artifact,
            character_orientation="image",
            prompt="gentle movement",
            keep_original_sound=False,  # Disable audio to simplify
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
    async def test_estimate_cost_modes(
        self, skip_if_no_fal_key, test_image_artifact, test_video_artifact
    ):
        """
        Test that cost estimation differs between orientation modes.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Image mode (up to 10s)
        inputs_image = KlingMotionControlInput(
            image_url=test_image_artifact,
            video_url=test_video_artifact,
            character_orientation="image",
        )
        cost_image = await self.generator.estimate_cost(inputs_image)

        # Video mode (up to 30s)
        inputs_video = KlingMotionControlInput(
            image_url=test_image_artifact,
            video_url=test_video_artifact,
            character_orientation="video",
        )
        cost_video = await self.generator.estimate_cost(inputs_video)

        # Video mode should cost 2x image mode (supports longer videos)
        assert cost_video == cost_image * 2

        # Sanity check on absolute costs
        assert cost_image > 0.0
        assert cost_image < 1.0  # Should be well under $1.00
        assert cost_video > 0.0
        assert cost_video < 1.0  # Should be well under $1.00
