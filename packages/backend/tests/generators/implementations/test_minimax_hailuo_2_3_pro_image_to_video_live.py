"""
Live API tests for FalMinimaxHailuo23ProImageToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_minimax_hailuo_2_3_pro_image_to_video_live.py -v
        -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_minimax_hailuo_2_3_pro_image_to_video_live.py -v
        -m live_api

Or run all Fal live tests:
    pytest -m live_fal -v

Note: Video generation is more expensive than image generation.
These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.minimax_hailuo_2_3_pro_image_to_video import (
    FalMinimaxHailuo23ProImageToVideoGenerator,
    MinimaxHailuo23ProImageToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


@pytest.fixture
def test_image_artifact():
    """Provide sample image artifact for video generation testing."""
    # Use publicly accessible test image from placehold.co
    # Red square that will serve as the first frame
    # Minimum 300x300 required by MiniMax Hailuo API
    return ImageArtifact(
        generation_id="test_input_image",
        storage_url="https://placehold.co/300x300/ff0000/ff0000.png",
        format="png",
        width=300,
        height=300,
    )


class TestMinimaxHailuo23ProImageToVideoGeneratorLive:
    """Live API tests for FalMinimaxHailuo23ProImageToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalMinimaxHailuo23ProImageToVideoGenerator()
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
        Uses a simple prompt to minimize processing time.
        """
        # Create minimal input to reduce cost
        inputs = MinimaxHailuo23ProImageToVideoInput(
            prompt="gentle motion",
            image_url=test_image_artifact,
            prompt_optimizer=True,
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
        assert artifact.format == "mp4"

        # Verify 1080p resolution output if available
        if artifact.width is not None and artifact.height is not None:
            assert artifact.width == 1920
            assert artifact.height == 1080

    @pytest.mark.asyncio
    async def test_generate_with_optimizer_disabled(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
        test_image_artifact,
    ):
        """
        Test video generation with prompt optimizer disabled.

        This test verifies that the generator works with prompt_optimizer=False.
        """
        inputs = MinimaxHailuo23ProImageToVideoInput(
            prompt="simple camera movement",
            image_url=test_image_artifact,
            prompt_optimizer=False,
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
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp4"

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key, test_image_artifact):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = MinimaxHailuo23ProImageToVideoInput(
            prompt="test",
            image_url=test_image_artifact,
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Sanity check - should be under $1 per video
        assert isinstance(estimated_cost, float)
