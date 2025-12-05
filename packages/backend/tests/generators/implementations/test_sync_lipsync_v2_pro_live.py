"""
Live API tests for FalSyncLipsyncV2ProGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_sync_lipsync_v2_pro_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_sync_lipsync_v2_pro_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v

Note: These tests use example video and audio URLs from Fal.ai's documentation
since the generator requires artifact inputs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact, VideoArtifact
from boards.generators.implementations.fal.video.sync_lipsync_v2_pro import (
    FalSyncLipsyncV2ProGenerator,
    SyncLipsyncV2ProInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestSyncLipsyncV2ProGeneratorLive:
    """Live API tests for FalSyncLipsyncV2ProGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalSyncLipsyncV2ProGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic lip-sync generation with pro model.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses the dedicated pro endpoint for high-quality results.

        Note: Uses example video and audio from Fal.ai documentation since
        this generator requires artifact inputs.
        """
        # Create video and audio artifacts using example URLs from Fal.ai docs
        # These are publicly accessible example files from the API documentation
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/tiger/IugLCDJRIoGqvqTa-EJTr_3wg74vCqyNuQ-IiBd77MM_output.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://fal.media/files/lion/vyFWygmZsIZlUO4s0nr2n.wav",
            format="wav",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Create input with default sync mode
        inputs = SyncLipsyncV2ProInput(
            video=video_artifact,
            audio=audio_artifact,
            sync_mode="cut_off",  # Default sync mode
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
        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "mp4"

    @pytest.mark.asyncio
    async def test_generate_with_loop_sync_mode(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test lip-sync generation with loop sync mode.

        Verifies that different sync modes are correctly processed by the pro endpoint.
        """
        # Create artifacts using example URLs
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/tiger/IugLCDJRIoGqvqTa-EJTr_3wg74vCqyNuQ-IiBd77MM_output.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://fal.media/files/lion/vyFWygmZsIZlUO4s0nr2n.wav",
            format="wav",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Test with loop sync mode
        inputs = SyncLipsyncV2ProInput(
            video=video_artifact,
            audio=audio_artifact,
            sync_mode="loop",  # Test different sync mode
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
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable for the pro model.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Create dummy artifacts (not actually used for cost estimation)
        video_artifact = VideoArtifact(
            generation_id="test",
            storage_url="https://example.com/test.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=None,
            fps=None,
        )
        audio_artifact = AudioArtifact(
            generation_id="test",
            storage_url="https://example.com/test.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        # Test pro model cost
        inputs = SyncLipsyncV2ProInput(
            video=video_artifact,
            audio=audio_artifact,
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1 per generation
