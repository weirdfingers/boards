"""
Live API tests for FalChatterboxTextToSpeechGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_chatterbox_text_to_speech_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_chatterbox_text_to_speech_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.chatterbox_text_to_speech import (
    ChatterboxTextToSpeechInput,
    FalChatterboxTextToSpeechGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestChatterboxTextToSpeechGeneratorLive:
    """Live API tests for FalChatterboxTextToSpeechGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalChatterboxTextToSpeechGenerator()
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
        inputs = ChatterboxTextToSpeechInput(
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
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_generate_with_emotive_tags(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test speech generation with emotive tags.

        Verifies that emotive tags like <laugh> are processed correctly.
        """
        # Use emotive tags in text
        inputs = ChatterboxTextToSpeechInput(
            text="That's hilarious! <laugh>",
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
        assert artifact.storage_url is not None
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with custom exaggeration and temperature.

        Verifies that custom parameters are correctly processed.
        """
        inputs = ChatterboxTextToSpeechInput(
            text="Testing custom params.",
            exaggeration=0.5,
            temperature=1.0,
            cfg=0.7,
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
        assert artifact.storage_url is not None

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Test with any text
        inputs = ChatterboxTextToSpeechInput(text="Test")
        cost = await self.generator.estimate_cost(inputs)

        # Verify fixed cost
        assert cost == 0.03

        # Sanity check on absolute costs
        assert cost > 0.0
        assert cost < 0.10  # Should be well under $0.10 per generation
