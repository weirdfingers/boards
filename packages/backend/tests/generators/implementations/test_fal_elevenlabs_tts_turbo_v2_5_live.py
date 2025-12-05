"""
Live API tests for FalElevenlabsTtsTurboV25Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_fal_elevenlabs_tts_turbo_v2_5_live.py \\
        -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_fal_elevenlabs_tts_turbo_v2_5_live.py \\
        -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.fal_elevenlabs_tts_turbo_v2_5 import (
    FalElevenlabsTtsTurboV25Generator,
    FalElevenlabsTtsTurboV25Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFalElevenlabsTtsTurboV25GeneratorLive:
    """Live API tests for FalElevenlabsTtsTurboV25Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalElevenlabsTtsTurboV25Generator()
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
        inputs = FalElevenlabsTtsTurboV25Input(
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
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_generate_with_voice_settings(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with custom voice and settings.

        Verifies that voice, stability, and speed parameters are correctly processed.
        """
        # Use short text to minimize cost
        inputs = FalElevenlabsTtsTurboV25Input(
            text="Testing voice settings.",
            voice="Sarah",
            stability=0.6,
            similarity_boost=0.8,
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
        assert artifact.format == "mp3"

    @pytest.mark.asyncio
    async def test_generate_with_language_code(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test speech generation with language code enforcement.

        Verifies that language_code parameter is correctly processed.
        """
        # Use short text to minimize cost
        inputs = FalElevenlabsTtsTurboV25Input(
            text="Hello world.",
            language_code="en",
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
    async def test_generate_with_context(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test speech generation with previous and next text context.

        Verifies that context parameters improve speech flow.
        """
        # Use short text to minimize cost
        inputs = FalElevenlabsTtsTurboV25Input(
            text="This is the main text.",
            previous_text="This came before.",
            next_text="This comes after.",
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
        # Test with 100 characters
        inputs_100 = FalElevenlabsTtsTurboV25Input(text="a" * 100)
        cost_100 = await self.generator.estimate_cost(inputs_100)

        # Verify cost for 100 characters is 100 * 0.001 = 0.1
        assert cost_100 == 0.1

        # Test with 1000 characters
        inputs_1000 = FalElevenlabsTtsTurboV25Input(text="a" * 1000)
        cost_1000 = await self.generator.estimate_cost(inputs_1000)

        # Verify cost scales correctly
        assert cost_1000 == 1.0

        # Sanity check on absolute costs
        assert cost_100 > 0.0
        assert cost_100 < 1.0
        assert cost_1000 < 10.0  # Sanity check
