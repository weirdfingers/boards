"""
Live API tests for FalElevenlabsSoundEffectsV2Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_elevenlabs_sound_effects_v2_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_elevenlabs_sound_effects_v2_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.fal.audio.elevenlabs_sound_effects_v2 import (
    ElevenlabsSoundEffectsV2Input,
    FalElevenlabsSoundEffectsV2Generator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestElevenlabsSoundEffectsV2GeneratorLive:
    """Live API tests for FalElevenlabsSoundEffectsV2Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalElevenlabsSoundEffectsV2Generator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test basic sound effect generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Use short duration to minimize cost
        inputs = ElevenlabsSoundEffectsV2Input(
            text="Bell ring",  # Simple sound effect
            duration_seconds=1.0,  # Short duration to reduce cost
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
    async def test_generate_with_auto_duration(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test sound effect generation with auto-determined duration.

        Verifies that duration_seconds=None allows the model to determine
        optimal duration from the prompt.
        """
        inputs = ElevenlabsSoundEffectsV2Input(
            text="Quick snap",  # Simple sound
            # duration_seconds=None is the default
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
    async def test_generate_with_high_prompt_influence(
        self, skip_if_no_fal_key, dummy_context, cost_logger
    ):
        """
        Test sound effect generation with high prompt influence.

        Verifies that prompt_influence parameter affects generation
        (higher values = less variation, more adherence to prompt).
        """
        inputs = ElevenlabsSoundEffectsV2Input(
            text="Water drop",
            duration_seconds=1.0,
            prompt_influence=0.8,  # High influence for precise sound
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
    async def test_generate_with_loop(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test sound effect generation with loop enabled.

        Verifies that loop=True creates a sound effect that loops smoothly.
        """
        inputs = ElevenlabsSoundEffectsV2Input(
            text="Ambient hum",
            duration_seconds=2.0,
            loop=True,  # Create looping sound
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
    async def test_generate_with_pcm_format(self, skip_if_no_fal_key, dummy_context, cost_logger):
        """
        Test sound effect generation with PCM output format.

        Verifies that different output formats work correctly.
        """
        inputs = ElevenlabsSoundEffectsV2Input(
            text="Click",
            duration_seconds=0.5,  # Very short for minimal cost
            output_format="pcm_44100",  # PCM format instead of MP3
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
        assert artifact.format == "pcm"

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        inputs = ElevenlabsSoundEffectsV2Input(text="Test")
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is fixed cost
        assert estimated_cost == 0.055

        # Test with different parameters - cost should remain the same
        inputs_long = ElevenlabsSoundEffectsV2Input(
            text="Long test description",
            duration_seconds=22.0,
        )
        cost_long = await self.generator.estimate_cost(inputs_long)

        # Cost should be the same regardless of duration
        assert cost_long == 0.055

        # Sanity check on absolute cost
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1
