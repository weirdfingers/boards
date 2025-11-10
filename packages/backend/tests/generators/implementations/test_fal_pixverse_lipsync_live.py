"""
Live API tests for FalPixverseLipsyncGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_fal_pixverse_lipsync_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_fal_pixverse_lipsync_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v

Note: These tests use example video and audio URLs from Fal.ai's documentation
since the generator requires artifact inputs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact, VideoArtifact
from boards.generators.implementations.fal.video.fal_pixverse_lipsync import (
    FalPixverseLipsyncGenerator,
    PixverseLipsyncInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestPixverseLipsyncGeneratorLive:
    """Live API tests for FalPixverseLipsyncGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalPixverseLipsyncGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_with_text_tts(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test basic lip-sync generation with text-to-speech.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses TTS with minimal text to minimize cost.

        Note: Uses example video from Fal.ai documentation.
        """
        # Create video artifact using example URL from Fal.ai docs
        # This is a publicly accessible example file
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/penguin/T-ONORYMYLoEOB9lXryA2_IKEy3yAyi1evJGBAkXGZx_output.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )

        # Create minimal input with short text to reduce cost
        inputs = PixverseLipsyncInput(
            video_url=video_artifact, text="Hello, this is a test.", voice_id="Auto"
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
    async def test_generate_with_audio(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test lip-sync generation with audio input.

        Verifies that the generator works with provided audio instead of TTS.
        Uses example video and audio from Fal.ai documentation.
        """
        # Create video artifact using example URL
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/penguin/T-ONORYMYLoEOB9lXryA2_IKEy3yAyi1evJGBAkXGZx_output.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )

        # Create audio artifact using example URL
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://v3.fal.media/files/monkey/k4iyN8bJZWwJXMKH-pO9r_speech.mp3",
            format="mp3",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Create input with audio
        inputs = PixverseLipsyncInput(
            video_url=video_artifact, audio_url=audio_artifact, voice_id="Auto"
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
        assert artifact.format == "mp4"

    @pytest.mark.asyncio
    async def test_generate_with_different_voice(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test lip-sync generation with different TTS voice.

        Verifies that voice selection works correctly.
        Uses minimal text to reduce cost.
        """
        # Create video artifact
        video_artifact = VideoArtifact(
            generation_id="example_video",
            storage_url="https://v3.fal.media/files/penguin/T-ONORYMYLoEOB9lXryA2_IKEy3yAyi1evJGBAkXGZx_output.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=5.0,
            fps=30.0,
        )

        # Test with a specific voice (Emily)
        inputs = PixverseLipsyncInput(
            video_url=video_artifact, text="Testing voice.", voice_id="Emily"
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

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Create dummy artifacts for cost estimation
        video_artifact = VideoArtifact(
            generation_id="test",
            storage_url="https://example.com/test.mp4",
            format="mp4",
            width=1920,
            height=1080,
            duration=10.0,  # 10 seconds
            fps=None,
        )
        audio_artifact = AudioArtifact(
            generation_id="test",
            storage_url="https://example.com/test.wav",
            format="wav",
            duration=10.0,
            sample_rate=None,
            channels=None,
        )

        # Test cost with audio (no TTS)
        inputs_audio = PixverseLipsyncInput(video_url=video_artifact, audio_url=audio_artifact)
        cost_audio = await self.generator.estimate_cost(inputs_audio)

        # Should be 10 seconds * $0.04 = $0.40
        assert cost_audio == pytest.approx(0.40, rel=0.01)

        # Test cost with TTS (100 characters)
        text_100_chars = "A" * 100
        inputs_tts = PixverseLipsyncInput(video_url=video_artifact, text=text_100_chars)
        cost_tts = await self.generator.estimate_cost(inputs_tts)

        # Should be (10 seconds * $0.04) + (100 chars * $0.24/100) = $0.40 + $0.24 = $0.64
        expected_tts_cost = 0.40 + 0.24
        assert cost_tts == pytest.approx(expected_tts_cost, rel=0.01)

        # Verify TTS is more expensive than audio-only
        assert cost_tts > cost_audio

        # Verify costs are in reasonable range
        assert cost_audio > 0.0
        assert cost_audio < 5.0  # Sanity check
        assert cost_tts < 10.0  # Sanity check
