"""
Live API tests for FalMinimaxSpeech26HdGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_fal_minimax_speech_26_hd_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_fal_minimax_speech_26_hd_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.fal_minimax_speech_26_hd import (
    AudioSetting,
    FalMinimaxSpeech26HdGenerator,
    FalMinimaxSpeech26HdInput,
    VoiceSetting,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFalMinimaxSpeech26HdGeneratorLive:
    """Live API tests for FalMinimaxSpeech26HdGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalMinimaxSpeech26HdGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic speech generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Use short text to minimize cost
        inputs = FalMinimaxSpeech26HdInput(
            prompt="Hello.",  # Very short to reduce cost
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) == 1

        # Verify artifact properties
        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_generate_with_voice_settings(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with custom voice settings.

        Verifies that voice_setting parameters are correctly processed.
        """
        # Use short text to minimize cost
        inputs = FalMinimaxSpeech26HdInput(
            prompt="Testing voice settings.",
            voice_setting=VoiceSetting(
                voice_id="Wise_Woman",
                speed=1.1,
                pitch=0,
                vol=1.0,
            ),
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_generate_with_audio_settings(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with custom audio settings.

        Verifies that audio_setting parameters (format, sample rate, etc.) are correctly processed.
        """
        # Use short text to minimize cost
        inputs = FalMinimaxSpeech26HdInput(
            prompt="Testing audio settings.",
            audio_setting=AudioSetting(
                format="flac",
                sample_rate=44100,
                channel=2,
                bitrate=256000,
            ),
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "flac"

    @pytest.mark.asyncio
    async def test_generate_with_language_boost(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with language boost.

        Verifies that language_boost parameter is correctly processed.
        """
        # Use short text to minimize cost
        inputs = FalMinimaxSpeech26HdInput(
            prompt="Hello world.",
            language_boost="English",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = FalMinimaxSpeech26HdInput(prompt="Test prompt")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is reasonable for HD version ($0.015 per generation)
        assert estimated_cost == 0.015
        assert estimated_cost > 0.0
        assert estimated_cost < 0.05  # Sanity check - should be under $0.05
