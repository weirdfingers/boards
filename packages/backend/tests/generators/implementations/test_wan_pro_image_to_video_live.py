"""
Live API tests for FalWanProImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_wan_pro_image_to_video_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_wan_pro_image_to_video_live.py -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is expensive. This test uses a small input image to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.wan_pro_image_to_video import (
    FalWanProImageToVideoGenerator,
    WanProImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide sample image artifact for video generation testing."""
    # Use small publicly accessible test image from placehold.co
    return ImageArtifact(
        generation_id="test_input_image",
        storage_url="https://placehold.co/256x256/0088ff/ffffff.png?text=Test",
        format="png",
        width=256,
        height=256,
    )


class TestWanProImageToVideoGeneratorLive:
    """Live API tests for FalWanProImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalWanProImageToVideoGenerator()
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
        Uses a small input image and simple prompt to minimize cost.
        """
        # Create minimal input to reduce cost
        inputs = WanProImageToVideoInput(
            image=test_image_artifact,
            prompt="gentle movement",  # Short, simple prompt
            enable_safety_checker=True,
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
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.duration is not None and artifact.duration > 0
        assert artifact.format == "mp4"

        # Verify expected dimensions for 1080p output if available
        if artifact.height is not None and artifact.width is not None:
            assert artifact.height == 1080 or artifact.width == 1920

        # Verify FPS (should be 30fps)
        if artifact.fps is not None:
            assert artifact.fps == 30

    @pytest.mark.asyncio
    async def test_generate_with_seed(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test video generation with seed for reproducibility.

        This test makes a real API call to verify seed parameter works.
        """
        # Create input with seed
        inputs = WanProImageToVideoInput(
            image=test_image_artifact,
            prompt="slow zoom in",
            seed=42,
            enable_safety_checker=True,
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 1

        # Verify artifact
        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_estimate_cost_reasonable(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = WanProImageToVideoInput(
            image=test_image_artifact,
            prompt="test",
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Sanity check - should be under $1 per video
