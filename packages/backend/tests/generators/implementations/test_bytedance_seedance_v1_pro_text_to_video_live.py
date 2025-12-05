"""
Live API tests for FalBytedanceSeedanceV1ProTextToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_bytedance_seedance_v1_pro_text_to_video_live.py \\
        -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_bytedance_seedance_v1_pro_text_to_video_live.py \\
        -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.bytedance_seedance_v1_pro_text_to_video import (
    BytedanceSeedanceV1ProTextToVideoInput,
    FalBytedanceSeedanceV1ProTextToVideoGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestBytedanceSeedanceV1ProTextToVideoGeneratorLive:
    """Live API tests for FalBytedanceSeedanceV1ProTextToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalBytedanceSeedanceV1ProTextToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings (480p, 2 seconds, square) to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            BytedanceSeedanceV1ProTextToVideoInput(prompt="test", resolution="480p", duration="2")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="A simple rotating cube",
            aspect_ratio="1:1",  # Square format (smallest resolution)
            resolution="480p",  # Lowest resolution
            duration="2",  # Shortest duration
            enable_safety_checker=True,
            camera_fixed=False,
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

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
        assert artifact.format == "mp4"
        assert artifact.duration == 2.0

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with custom parameters.

        Verifies that custom aspect ratio, resolution, and camera settings
        are correctly processed.
        """
        # Create input with custom parameters
        inputs = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="A serene mountain landscape at sunset",
            aspect_ratio="16:9",
            resolution="720p",  # Medium resolution to balance quality and cost
            duration="3",  # Short duration to minimize cost
            enable_safety_checker=True,
            camera_fixed=True,  # Fixed camera position
            seed=42,  # Use seed for reproducibility
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url.startswith("https://")
        # Expected dimensions: 16:9 at 720p = 1280x720
        assert artifact.width == 1280
        assert artifact.height == 720
        assert artifact.format == "mp4"
        assert artifact.duration == 3.0

    @pytest.mark.asyncio
    async def test_generate_portrait_video(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test video generation with portrait (9:16) aspect ratio.

        Verifies that portrait orientation is correctly handled.
        """
        # Create portrait input
        inputs = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="A person walking down a city street",
            aspect_ratio="9:16",
            resolution="480p",  # Low resolution to minimize cost
            duration="2",  # Shortest duration
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url.startswith("https://")
        # Portrait should have height > width
        assert (
            artifact.height is not None
            and artifact.width is not None
            and artifact.height > artifact.width
        )
        # Expected dimensions: 9:16 at 480p = 270x480
        assert artifact.width == 270
        assert artifact.height == 480
        assert artifact.format == "mp4"

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Test default settings (1080p, 5 seconds)
        inputs_default = BytedanceSeedanceV1ProTextToVideoInput(prompt="test")
        cost_default = await self.generator.estimate_cost(inputs_default)

        # Test minimum cost (480p, 2 seconds)
        inputs_min = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="test", resolution="480p", duration="2"
        )
        cost_min = await self.generator.estimate_cost(inputs_min)

        # Test maximum cost (1080p, 12 seconds)
        inputs_max = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="test", resolution="1080p", duration="12"
        )
        cost_max = await self.generator.estimate_cost(inputs_max)

        # Verify estimates are in reasonable range
        assert cost_min > 0.0
        assert cost_min < cost_default < cost_max
        assert cost_max < 1.0  # Sanity check - should be under $1.00

        # Verify resolution affects cost
        inputs_720p = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="test", resolution="720p", duration="5"
        )
        cost_720p = await self.generator.estimate_cost(inputs_720p)
        assert cost_min < cost_720p < cost_default  # 720p should be between 480p and 1080p

    @pytest.mark.asyncio
    async def test_estimate_cost_duration_scaling(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with duration.

        This doesn't make an API call, just verifies the cost logic.
        """
        # Test different durations at same resolution
        inputs_2s = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="test", resolution="720p", duration="2"
        )
        cost_2s = await self.generator.estimate_cost(inputs_2s)

        inputs_5s = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="test", resolution="720p", duration="5"
        )
        cost_5s = await self.generator.estimate_cost(inputs_5s)

        inputs_12s = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="test", resolution="720p", duration="12"
        )
        cost_12s = await self.generator.estimate_cost(inputs_12s)

        # Longer videos should cost more
        assert cost_2s < cost_5s < cost_12s

        # Sanity check on absolute costs
        assert cost_2s > 0.0
        assert cost_12s < 1.0  # Even the longest video should be under $1.00
