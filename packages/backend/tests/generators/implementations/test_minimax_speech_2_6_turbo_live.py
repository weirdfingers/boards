"""
Live API tests for FalMinimaxSpeech26TurboGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_minimax_speech_2_6_turbo_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_minimax_speech_2_6_turbo_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.minimax_speech_2_6_turbo import (
    FalMinimaxSpeech26TurboGenerator,
    MinimaxSpeech26TurboInput,
    VoiceSetting,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestMinimaxSpeech26TurboGeneratorLive:
    """Live API tests for FalMinimaxSpeech26TurboGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalMinimaxSpeech26TurboGenerator()
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
        inputs = MinimaxSpeech26TurboInput(
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
        inputs = MinimaxSpeech26TurboInput(
            prompt="Testing voice settings.",
            voice_setting=VoiceSetting(
                voice_id="Wise_Woman",
                speed=1.1,
                pitch=0.0,
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
    async def test_generate_with_pause_markers(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with pause markers.

        Verifies that custom pause markers <#x#> are supported.
        """
        # Use pause markers in text (short to minimize cost)
        inputs = MinimaxSpeech26TurboInput(
            prompt="Hello<#0.5#>world.",  # 0.5 second pause
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
        # Test with 1000 characters (should be $0.06)
        inputs_1000 = MinimaxSpeech26TurboInput(prompt="a" * 1000)
        cost_1000 = await self.generator.estimate_cost(inputs_1000)

        # Verify cost for 1000 characters is $0.06
        assert cost_1000 == 0.06

        # Test with 100 characters
        inputs_100 = MinimaxSpeech26TurboInput(prompt="a" * 100)
        cost_100 = await self.generator.estimate_cost(inputs_100)

        # Verify cost scales correctly
        assert cost_100 == 0.006

        # Sanity check on absolute costs
        assert cost_100 > 0.0
        assert cost_100 < 0.01  # Should be well under $0.01 for 100 chars
        assert cost_1000 < 0.10  # Should be well under $0.10 for 1000 chars

    @pytest.mark.asyncio
    async def test_generate_with_language_boost(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with language boost.

        Verifies that language_boost parameter is correctly processed.
        """
        # Use short text to minimize cost
        inputs = MinimaxSpeech26TurboInput(
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
