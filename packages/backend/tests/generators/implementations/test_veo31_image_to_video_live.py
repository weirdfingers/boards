"""
Live API tests for FalVeo31ImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_veo31_image_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_veo31_image_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is more expensive than image generation.
These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.veo31_image_to_video import (
    FalVeo31ImageToVideoGenerator,
    Veo31ImageToVideoInput,
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


class TestVeo31ImageToVideoGeneratorLive:
    """Live API tests for FalVeo31ImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalVeo31ImageToVideoGenerator()
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
        """
        # Create minimal input to reduce cost
        inputs = Veo31ImageToVideoInput(
            prompt="gentle zoom in",
            image=test_image_artifact,
            resolution="720p",  # Lower resolution to reduce cost
            aspect_ratio="16:9",
            duration="4s",  # Shortest duration to reduce cost
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
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.duration is not None and artifact.duration > 0
        assert artifact.format == "mp4"

        # Verify expected dimensions for 720p 16:9
        assert artifact.width == 1280
        assert artifact.height == 720

        # Verify duration matches requested
        assert artifact.duration == 4

    @pytest.mark.asyncio
    async def test_generate_portrait_9_16(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test portrait video generation (9:16 aspect ratio).

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal settings to reduce cost.
        """
        # Create portrait video input
        inputs = Veo31ImageToVideoInput(
            prompt="slow pan down",
            image=test_image_artifact,
            resolution="720p",
            aspect_ratio="9:16",  # Portrait mode
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

        # Verify expected dimensions for 720p 9:16 (portrait)
        assert artifact.width == 720
        assert artifact.height == 1280

    @pytest.mark.asyncio
    async def test_estimate_cost_audio_discount(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that cost estimation reflects 50% discount when audio is disabled.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Cost with audio
        inputs_with_audio = Veo31ImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            generate_audio=True,
        )
        cost_with_audio = await self.generator.estimate_cost(inputs_with_audio)

        # Cost without audio (should be 50% of base)
        inputs_without_audio = Veo31ImageToVideoInput(
            prompt="test",
            image=test_image_artifact,
            generate_audio=False,
        )
        cost_without_audio = await self.generator.estimate_cost(inputs_without_audio)

        # Verify audio discount
        assert cost_without_audio == cost_with_audio * 0.5

        # Sanity check on absolute costs
        assert cost_with_audio > 0.0
        assert cost_with_audio < 1.0  # Should be under $1 per video
