"""
Live API tests for FalCreatifyLipsyncGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_creatify_lipsync_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_creatify_lipsync_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v

Note: These tests use example video and audio URLs from Fal.ai's documentation
since the generator requires artifact inputs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact, VideoArtifact
from boards.generators.implementations.fal.video.creatify_lipsync import (
    CreatifyLipsyncInput,
    FalCreatifyLipsyncGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestCreatifyLipsyncGeneratorLive:
    """Live API tests for FalCreatifyLipsyncGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalCreatifyLipsyncGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic lip-sync generation with default parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses example video and audio from Fal.ai documentation.
        """
        # Create video and audio artifacts using example URLs from Fal.ai docs
        # These are publicly accessible example files
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/monkey/GzfGN-LfnbobjM9h2g5PF_Eduardo.mov",
            format="mov",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://v3.fal.media/files/penguin/IjB1sco-ydVA-szm3a1Rm_E_voice.mp3",
            format="mp3",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Create minimal input with default loop=True
        inputs = CreatifyLipsyncInput(
            video=video_artifact,
            audio=audio_artifact,
            loop=True,
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
        assert artifact.width > 0
        assert artifact.height > 0
        assert artifact.format == "mp4"

    @pytest.mark.asyncio
    async def test_generate_with_loop_false(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test lip-sync generation with loop disabled.

        Verifies that the loop parameter is correctly processed.
        """
        # Create artifacts using example URLs
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/monkey/GzfGN-LfnbobjM9h2g5PF_Eduardo.mov",
            format="mov",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://v3.fal.media/files/penguin/IjB1sco-ydVA-szm3a1Rm_E_voice.mp3",
            format="mp3",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Test with loop disabled
        inputs = CreatifyLipsyncInput(
            video=video_artifact,
            audio=audio_artifact,
            loop=False,
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
        assert artifact.width > 0
        assert artifact.height > 0

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

        # Test cost estimation
        inputs = CreatifyLipsyncInput(
            video=video_artifact,
            audio=audio_artifact,
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1 per generation
