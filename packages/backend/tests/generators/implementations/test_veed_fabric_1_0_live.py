"""
Live API tests for FalVeedFabric10Generator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_veed_fabric_1_0_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_veed_fabric_1_0_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v

Note: These tests use example image and audio URLs since the generator requires
artifact inputs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact, ImageArtifact, VideoArtifact
from boards.generators.implementations.fal.video.veed_fabric_1_0 import (
    FalVeedFabric10Generator,
    VeedFabric10Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestVeedFabric10GeneratorLive:
    """Live API tests for FalVeedFabric10Generator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalVeedFabric10Generator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic VEED Fabric 1.0 generation.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 480p resolution to minimize cost.
        """
        # Create image artifact with a sample portrait image
        image_artifact = ImageArtifact(
            generation_id="example_image",
            storage_url="https://placehold.co/512x512/ff0000/ff0000.png",
            format="png",
            width=512,
            height=512,
        )
        # Create audio artifact with a short sample
        # Using a publicly accessible short audio clip
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://v3.fal.media/files/rabbit/Ql3ade3wEKlZXRQLRbhxm_tts.mp3",
            format="mp3",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Create input with lowest resolution to reduce cost
        inputs = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
            resolution="480p",
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
        image_artifact = ImageArtifact(
            generation_id="test",
            storage_url="https://example.com/test.png",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="test",
            storage_url="https://example.com/test.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        inputs = VeedFabric10Input(
            image_url=image_artifact,
            audio_url=audio_artifact,
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # Verify estimate is in reasonable range
        assert estimated_cost > 0.0
        assert estimated_cost < 1.0  # Should be well under $1 per generation
