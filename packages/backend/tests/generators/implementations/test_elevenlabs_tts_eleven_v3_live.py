"""
Live API tests for FalElevenlabsTtsElevenV3Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_elevenlabs_tts_eleven_v3_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_elevenlabs_tts_eleven_v3_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.elevenlabs_tts_eleven_v3 import (
    ElevenlabsTtsElevenV3Input,
    FalElevenlabsTtsElevenV3Generator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestElevenlabsTtsElevenV3GeneratorLive:
    """Live API tests for FalElevenlabsTtsElevenV3Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalElevenlabsTtsElevenV3Generator()
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
        inputs = ElevenlabsTtsElevenV3Input(
            text="Hello.",  # Very short to reduce cost
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
        assert artifact.format in ["mp3", "wav", "ogg"]

    @pytest.mark.asyncio
    async def test_generate_with_custom_voice(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test speech generation with custom voice.

        Verifies that voice parameter is correctly processed.
        """
        # Use short text to minimize cost with custom voice
        inputs = ElevenlabsTtsElevenV3Input(
            text="Testing custom voice.",
            voice="Sarah",
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
    async def test_generate_with_voice_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with custom voice parameters.

        Verifies that stability, similarity_boost, style, and speed parameters
        are correctly processed.
        """
        # Use short text with custom voice parameters
        inputs = ElevenlabsTtsElevenV3Input(
            text="Testing voice parameters.",
            stability=0.7,
            similarity_boost=0.8,
            style=0.2,
            speed=1.1,
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
        # Test with 1000 characters (should be $0.10)
        inputs = ElevenlabsTtsElevenV3Input(text="a" * 1000)
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Should be $0.10 for 1000 characters
        assert estimated_cost == pytest.approx(0.10)
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Sanity check

        # Test with 100 characters (should be $0.01)
        inputs_short = ElevenlabsTtsElevenV3Input(text="a" * 100)
        estimated_cost_short = await self.generator.estimate_cost(inputs_short)

        assert estimated_cost_short == pytest.approx(0.01)
        assert estimated_cost_short < estimated_cost
