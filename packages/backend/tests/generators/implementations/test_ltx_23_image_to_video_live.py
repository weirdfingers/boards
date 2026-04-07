"""
Live API tests for FalLtx23ImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_ltx_23_image_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_ltx_23_image_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.ltx_23_image_to_video import (
    FalLtx23ImageToVideoGenerator,
    Ltx23ImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide a sample image artifact for video generation testing."""
    image = ImageArtifact(
        generation_id="test_image",
        storage_url="https://placehold.co/512x512/ff9900/ffffff.png",
        format="png",
        width=512,
        height=512,
    )
    return image


class TestLtx23ImageToVideoGeneratorLive:
    """Live API tests for FalLtx23ImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalLtx23ImageToVideoGenerator()
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
        Test basic image-to-video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses shortest duration and lowest resolution to reduce cost.
        """
        inputs = Ltx23ImageToVideoInput(
            image=test_image_artifact,
            prompt="The image gently zooms in with a slow pan",
            duration=6,  # Shortest available duration
            resolution="1080p",  # Lowest available resolution
            aspect_ratio="auto",
            fps=24,
            generate_audio=False,  # Skip audio to reduce cost/time
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, image_resolving_context)

        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "mp4"
        assert artifact.duration is not None
        assert artifact.duration > 0
