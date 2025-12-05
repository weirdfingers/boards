"""
Live API tests for FalVeedLipsyncGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_veed_lipsync_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_veed_lipsync_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v

Note: These tests use example video and audio URLs from Fal.ai's documentation
since the generator requires artifact inputs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact, VideoArtifact
from boards.generators.implementations.fal.video.veed_lipsync import (
    FalVeedLipsyncGenerator,
    VeedLipsyncInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestVeedLipsyncGeneratorLive:
    """Live API tests for FalVeedLipsyncGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalVeedLipsyncGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic VEED lip-sync generation.

        This test makes a real API call to Fal.ai and will consume credits.

        Note: Uses example video and audio from Fal.ai documentation since
        this generator requires artifact inputs.
        """
        # Create video and audio artifacts using example URLs from Fal.ai docs
        # Example video URL from veed/lipsync documentation
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/monkey/q1fDPhrpfjfsaRmbhTed4_influencer.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )
        # Example audio URL from veed/lipsync documentation
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://v3.fal.media/files/rabbit/Ql3ade3wEKlZXRQLRbhxm_tts.mp3",
            format="mp3",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Create input
        inputs = VeedLipsyncInput(
            video_url=video_artifact,
            audio_url=audio_artifact,
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
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

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

        inputs = VeedLipsyncInput(
            video_url=video_artifact,
            audio_url=audio_artifact,
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1 per generation
