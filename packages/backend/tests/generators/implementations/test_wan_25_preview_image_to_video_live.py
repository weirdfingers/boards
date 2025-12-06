"""
Live API tests for FalWan25PreviewImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_wan_25_preview_image_to_video_live.py \
        -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_wan_25_preview_image_to_video_live.py \
        -v -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is expensive. This test uses a small input image and
short duration to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.wan_25_preview_image_to_video import (
    FalWan25PreviewImageToVideoGenerator,
    Wan25PreviewImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide sample image artifact for video generation testing."""
    # Use small publicly accessible test image from placehold.co
    return ImageArtifact(
        generation_id="test_input_image",
        storage_url="https://placehold.co/512x512/0088ff/ffffff.png?text=Test",
        format="png",
        width=512,
        height=512,
    )


class TestWan25PreviewImageToVideoGeneratorLive:
    """Live API tests for FalWan25PreviewImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalWan25PreviewImageToVideoGenerator()
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
        Uses a small input image, short duration, and low resolution to minimize cost.
        """
        # Create minimal input to reduce cost
        inputs = Wan25PreviewImageToVideoInput(
            image=test_image_artifact,
            prompt="gentle camera movement",  # Short, simple prompt
            duration="5",  # Shortest duration
            resolution="480p",  # Lowest resolution
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
        Uses minimal settings to reduce cost.
        """
        # Create input with seed
        inputs = Wan25PreviewImageToVideoInput(
            image=test_image_artifact,
            prompt="slow zoom out",
            duration="5",
            resolution="480p",
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
        # Test 5 second video
        inputs_5s = Wan25PreviewImageToVideoInput(
            image=test_image_artifact,
            prompt="test",
            duration="5",
        )
        estimated_cost_5s = await self.generator.estimate_cost(inputs_5s)

        # Test 10 second video
        inputs_10s = Wan25PreviewImageToVideoInput(
            image=test_image_artifact,
            prompt="test",
            duration="10",
        )
        estimated_cost_10s = await self.generator.estimate_cost(inputs_10s)

        # Verify estimates are in reasonable range
        assert estimated_cost_5s > 0.0
        assert estimated_cost_5s < 1.0  # Sanity check - should be under $1 per video
        assert estimated_cost_10s > estimated_cost_5s  # 10s should cost more than 5s
        assert estimated_cost_10s < 2.0  # Should be under $2
