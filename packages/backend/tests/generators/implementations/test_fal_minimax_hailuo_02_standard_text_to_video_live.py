"""
Live API tests for FalMinimaxHailuo02StandardTextToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/\
test_fal_minimax_hailuo_02_standard_text_to_video_live.py -v

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/\
test_fal_minimax_hailuo_02_standard_text_to_video_live.py -v

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.video.fal_minimax_hailuo_02_standard_text_to_video import (  # noqa: E501
    FalMinimaxHailuo02StandardTextToVideoGenerator,
    FalMinimaxHailuo02StandardTextToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFalMinimaxHailuo02StandardTextToVideoGeneratorLive:
    """Live API tests for FalMinimaxHailuo02StandardTextToVideoGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalMinimaxHailuo02StandardTextToVideoGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings (6-second duration) to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            FalMinimaxHailuo02StandardTextToVideoInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="A simple rotating cube in space",
            duration="6",  # Shortest duration (default)
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
        assert artifact.width == 1360  # 768p width
        assert artifact.height == 768  # 768p height
        assert artifact.format == "mp4"
        assert artifact.duration == 6.0

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with custom parameters.

        Verifies 10-second duration and disabled prompt optimizer.
        """
        # Create input with custom parameters
        inputs = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="A serene mountain landscape at sunset with gentle clouds",
            duration="10",  # Longer duration
            prompt_optimizer=False,  # Disable prompt optimization
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
        assert artifact.width == 1360
        assert artifact.height == 768
        assert artifact.format == "mp4"
        assert artifact.duration == 10.0

    @pytest.mark.asyncio
    async def test_generate_with_prompt_optimizer_enabled(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test video generation with prompt optimizer enabled (default).

        Verifies that prompt_optimizer=True works correctly.
        """
        # Create input with prompt optimizer explicitly enabled
        inputs = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="A futuristic city at night with neon lights",
            duration="6",  # Keep duration short to minimize cost
            prompt_optimizer=True,  # Explicitly enable (default)
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
        assert artifact.width == 1360
        assert artifact.height == 768
        assert artifact.format == "mp4"
        assert artifact.duration == 6.0

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_duration(self, skip_if_no_fal_key):
        """
        Test that cost estimation scales with duration.

        This doesn't make an API call, just verifies the cost logic.
        """
        # 6-second video (default)
        inputs_6s = FalMinimaxHailuo02StandardTextToVideoInput(prompt="test", duration="6")
        cost_6s = await self.generator.estimate_cost(inputs_6s)

        # 10-second video
        inputs_10s = FalMinimaxHailuo02StandardTextToVideoInput(prompt="test", duration="10")
        cost_10s = await self.generator.estimate_cost(inputs_10s)

        # 10-second should cost 1.67x the 6-second
        expected_cost_10s = cost_6s * 1.67
        assert cost_10s == expected_cost_10s

        # Sanity check on absolute costs
        assert cost_6s > 0.0
        assert cost_6s < 1.0  # Should be well under $1.00 per 6-second video
        assert cost_10s < 1.0  # Should be well under $1.00 per 10-second video
