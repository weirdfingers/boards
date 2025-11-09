"""
Live API tests for FalVeo31FirstLastFrameToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_veo31_first_last_frame_to_video_live.py -v
        -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_veo31_first_last_frame_to_video_live.py -v
        -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is more expensive than image generation.
These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.veo31_first_last_frame_to_video import (
    FalVeo31FirstLastFrameToVideoGenerator,
    Veo31FirstLastFrameToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifacts():
    """Provide sample image artifacts for video generation testing."""
    # Use small publicly accessible test images from placehold.co
    # First frame: red square
    first_frame = ImageArtifact(
        generation_id="test_first_frame",
        storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
        format="png",
        width=256,
        height=256,
    )

    # Last frame: blue square (different from first for transition testing)
    last_frame = ImageArtifact(
        generation_id="test_last_frame",
        storage_url="https://placehold.co/256x256/0000ff/0000ff.png",
        format="png",
        width=256,
        height=256,
    )

    return [first_frame, last_frame]


class TestVeo31FirstLastFrameToVideoGeneratorLive:
    """Live API tests for FalVeo31FirstLastFrameToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalVeo31FirstLastFrameToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic_720p(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifacts,
    ):
        """
        Test basic video generation with minimal parameters (720p, no audio).

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 720p resolution and disabled audio to minimize cost.
        """
        # Get test image artifacts (these are sample images from the fixture)
        first_frame = test_image_artifacts[0]
        last_frame = (
            test_image_artifacts[1] if len(test_image_artifacts) > 1 else test_image_artifacts[0]
        )

        # Create minimal input to reduce cost
        inputs = Veo31FirstLastFrameToVideoInput(
            first_frame=first_frame,
            last_frame=last_frame,
            prompt="smooth transition",
            resolution="720p",  # Lower resolution to reduce cost
            aspect_ratio="auto",
            generate_audio=False,  # Disable audio (50% cheaper)
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

        # Verify expected dimensions for 720p
        assert artifact.height == 720 or artifact.width == 1280

    @pytest.mark.asyncio
    async def test_estimate_cost_audio_discount(self, skip_if_no_fal_key, test_image_artifacts):
        """
        Test that cost estimation reflects 50% discount when audio is disabled.

        This doesn't make an API call, just verifies the cost logic.
        """
        first_frame = test_image_artifacts[0]
        last_frame = (
            test_image_artifacts[1] if len(test_image_artifacts) > 1 else test_image_artifacts[0]
        )

        # Cost with audio
        inputs_with_audio = Veo31FirstLastFrameToVideoInput(
            first_frame=first_frame,
            last_frame=last_frame,
            prompt="test",
            generate_audio=True,
        )
        cost_with_audio = await self.generator.estimate_cost(inputs_with_audio)

        # Cost without audio (should be 50% of base)
        inputs_without_audio = Veo31FirstLastFrameToVideoInput(
            first_frame=first_frame,
            last_frame=last_frame,
            prompt="test",
            generate_audio=False,
        )
        cost_without_audio = await self.generator.estimate_cost(inputs_without_audio)

        # Verify audio discount
        assert cost_without_audio == cost_with_audio * 0.5

        # Sanity check on absolute costs
        assert cost_with_audio > 0.0
        assert cost_with_audio < 1.0  # Should be under $1 per video
