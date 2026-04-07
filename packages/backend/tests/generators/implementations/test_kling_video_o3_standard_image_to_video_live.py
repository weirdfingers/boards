"""
Live API tests for FalKlingVideoO3StandardImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    pytest tests/generators/implementations/\
test_kling_video_o3_standard_image_to_video_live.py -v -m live_api
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.implementations.fal.video.kling_video_o3_standard_image_to_video import (
    FalKlingVideoO3StandardImageToVideoGenerator,
    KlingVideoO3StandardImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for video generation testing."""
    return ImageArtifact(
        generation_id="test_image",
        storage_url="https://placehold.co/512x512/ff9900/ffffff.png",
        format="png",
        width=512,
        height=512,
    )


class TestKlingVideoO3StandardImageToVideoGeneratorLive:
    """Live API tests for FalKlingVideoO3StandardImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKlingVideoO3StandardImageToVideoGenerator()
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
        inputs = KlingVideoO3StandardImageToVideoInput(
            prompt="gentle camera zoom",
            start_frame=test_image_artifact,
            duration="5",
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, image_resolving_context)

        assert result.outputs is not None
        assert len(result.outputs) == 1

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp4"
        assert artifact.duration is not None
        assert artifact.duration > 0
