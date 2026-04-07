"""
Live API tests for FalKlingVideoV3ProImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/\
        test_kling_video_v3_pro_image_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/\
        test_kling_video_v3_pro_image_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is more expensive than image generation.
These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.kling_video_v3_pro_image_to_video import (
    FalKlingVideoV3ProImageToVideoGenerator,
    KlingVideoV3ProImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for video generation testing."""
    # Use a small publicly accessible test image from placehold.co
    return ImageArtifact(
        generation_id="test_image",
        storage_url="https://placehold.co/512x512/ff9900/ffffff.png",
        format="png",
        width=512,
        height=512,
    )


class TestKlingVideoV3ProImageToVideoGeneratorLive:
    """Live API tests for FalKlingVideoV3ProImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKlingVideoV3ProImageToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings (5-second duration) to reduce cost.
        """
        # Create minimal input to reduce cost
        inputs = KlingVideoV3ProImageToVideoInput(
            prompt="gentle camera zoom",
            image_url=test_image_artifact,
            duration="5",  # Shortest duration
            generate_audio=False,  # Skip audio to reduce cost
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
        assert artifact.duration == 5.0
