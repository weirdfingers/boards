"""
Live API tests for FalVeo31FastImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_veo31_fast_image_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_veo31_fast_image_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation costs $0.10-$0.15 per second.
These tests use minimal settings (4s, no audio) to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.veo31_fast_image_to_video import (
    FalVeo31FastImageToVideoGenerator,
    Veo31FastImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for video generation testing."""
    # Use a small publicly accessible test image from placehold.co
    return ImageArtifact(
        generation_id="test_input_image",
        storage_url="https://placehold.co/256x256/ff0000/ff0000.png",
        format="png",
        width=256,
        height=256,
    )


class TestVeo31FastImageToVideoGeneratorLive:
    """Live API tests for FalVeo31FastImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalVeo31FastImageToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic_720p(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test basic video generation with minimal parameters (720p, 4s, no audio).

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 720p resolution, shortest duration (4s), and disabled audio to minimize cost.
        Cost: 4 seconds * $0.10 = $0.40
        """
        # Create minimal input to reduce cost
        inputs = Veo31FastImageToVideoInput(
            prompt="gentle zoom in",
            image=test_image_artifact,
            resolution="720p",  # Lower resolution to reduce cost
            aspect_ratio="auto",  # Use auto detection
            duration="4s",  # Shortest duration to reduce cost
            generate_audio=False,  # Disable audio (cheaper)
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
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.duration is not None and artifact.duration > 0
        assert artifact.format == "mp4"

        # Verify duration matches requested
        assert artifact.duration == 4

    @pytest.mark.asyncio
    async def test_generate_with_explicit_aspect_ratio(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test video generation with explicit 16:9 aspect ratio.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal settings to reduce cost.
        Cost: 4 seconds * $0.10 = $0.40
        """
        # Create input with explicit aspect ratio
        inputs = Veo31FastImageToVideoInput(
            prompt="slow pan across scene",
            image=test_image_artifact,
            resolution="720p",
            aspect_ratio="16:9",  # Explicit aspect ratio instead of auto
            duration="4s",
            generate_audio=False,
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
        assert artifact.format == "mp4"

        # Verify expected dimensions for 720p 16:9
        assert artifact.width == 1280
        assert artifact.height == 720

    @pytest.mark.asyncio
    async def test_estimate_cost_per_second_pricing(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that cost estimation reflects per-second pricing.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Test 4s with audio ($0.15/sec)
        inputs_4s_audio = Veo31FastImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            duration="4s",
            generate_audio=True,
        )
        cost_4s_audio = await self.generator.estimate_cost(inputs_4s_audio)
        assert cost_4s_audio == 4 * 0.15  # $0.60

        # Test 8s with audio ($0.15/sec)
        inputs_8s_audio = Veo31FastImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            duration="8s",
            generate_audio=True,
        )
        cost_8s_audio = await self.generator.estimate_cost(inputs_8s_audio)
        assert cost_8s_audio == 8 * 0.15  # $1.20

        # Test 6s without audio ($0.10/sec)
        inputs_6s_no_audio = Veo31FastImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            duration="6s",
            generate_audio=False,
        )
        cost_6s_no_audio = await self.generator.estimate_cost(inputs_6s_no_audio)
        assert cost_6s_no_audio == 6 * 0.10  # $0.60

        # Verify pricing scales linearly with duration
        assert cost_8s_audio == 2 * cost_4s_audio
