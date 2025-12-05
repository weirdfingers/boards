"""
Live API tests for FalMinimaxMusicV2Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_minimax_music_v2_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_minimax_music_v2_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.minimax_music_v2 import (
    FalMinimaxMusicV2Generator,
    MinimaxMusicV2Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestMinimaxMusicV2GeneratorLive:
    """Live API tests for FalMinimaxMusicV2Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalMinimaxMusicV2Generator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic music generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal settings to reduce cost.
        """
        # Create minimal input to reduce cost
        # Note: Music generation requires proper song structure in lyrics_prompt
        inputs = MinimaxMusicV2Input(
            prompt="Simple upbeat pop music with electronic beats",
            lyrics_prompt=(
                "[Verse]\nThis is a test song for verification\n[Chorus]\nSimple melody with rhythm"
            ),
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
        assert artifact.format == "mp3"
        # Default sample rate is 44100 when audio_setting is not provided
        assert artifact.sample_rate == 44100

    @pytest.mark.asyncio
    async def test_generate_with_default_settings(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test music generation without custom audio settings (using defaults).

        Verifies that the generator works correctly when audio_setting is not provided.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            MinimaxMusicV2Input(
                prompt="Test music prompt",
                lyrics_prompt="Test lyrics for music generation",
            )
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create input without audio_setting
        inputs = MinimaxMusicV2Input(
            prompt="Relaxing ambient music for meditation",
            lyrics_prompt="[Intro]\nCalm and peaceful sounds\n[Verse]\nGentle melodies",
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result
        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import AudioArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, AudioArtifact)
        assert artifact.storage_url is not None
        # Should use default format (mp3) when not specified
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_estimate_cost_is_reasonable(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = MinimaxMusicV2Input(
            prompt="Test music prompt",
            lyrics_prompt="Test lyrics for music generation",
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1.00
        # Based on typical music generation pricing
        assert 0.05 <= estimated_cost <= 0.15  # Expected range for music generation
