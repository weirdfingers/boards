"""
Live API tests for FalKlingVideoAiAvatarV2ProGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_kling_video_ai_avatar_v2_pro_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_kling_video_ai_avatar_v2_pro_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v

Note: These tests use example image and audio URLs to test the avatar generation.
Cost: ~$0.115/second of generated video.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact, ImageArtifact, VideoArtifact
from boards.generators.implementations.fal.video.kling_video_ai_avatar_v2_pro import (
    FalKlingVideoAiAvatarV2ProGenerator,
    KlingVideoAiAvatarV2ProInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestKlingVideoAiAvatarV2ProGeneratorLive:
    """Live API tests for FalKlingVideoAiAvatarV2ProGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalKlingVideoAiAvatarV2ProGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic avatar video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a portrait image and short audio to minimize cost.
        """
        # Create image artifact using a publicly accessible portrait image
        image_artifact = ImageArtifact(
            generation_id="example_image",
            storage_url="https://storage.googleapis.com/falserverless/example_inputs/kling_ai_avatar_input.jpg",
            format="png",
            width=512,
            height=512,
        )

        # Create audio artifact using a short test audio
        # Using a publicly accessible short audio file
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://v3.fal.media/files/rabbit/9_0ZG_geiWjZOmn9yscO6_output.mp3",
            format="mp3",
            duration=5.0,  # Short audio to minimize cost (~$0.575)
            sample_rate=44100,
            channels=2,
        )

        # Create minimal input with default prompt
        inputs = KlingVideoAiAvatarV2ProInput(
            image=image_artifact,
            audio=audio_artifact,
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

    @pytest.mark.asyncio
    async def test_generate_with_prompt(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test avatar video generation with custom prompt.

        Verifies that the prompt parameter is correctly processed.
        """
        # Create image artifact
        image_artifact = ImageArtifact(
            generation_id="example_image",
            storage_url="https://storage.googleapis.com/falserverless/example_inputs/kling_ai_avatar_input.jpg",
            format="png",
            width=512,
            height=512,
        )

        # Create audio artifact
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://v3.fal.media/files/rabbit/9_0ZG_geiWjZOmn9yscO6_output.mp3",
            format="mp3",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Test with custom prompt
        inputs = KlingVideoAiAvatarV2ProInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Generate natural, subtle facial movements",
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
        # Create dummy artifacts (used for cost estimation based on audio duration)
        image_artifact = ImageArtifact(
            generation_id="test",
            storage_url="https://storage.googleapis.com/falserverless/example_inputs/kling_ai_avatar_input.jpg",
            format="png",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="test",
            storage_url="https://v3.fal.media/files/rabbit/9_0ZG_geiWjZOmn9yscO6_output.mp3",
            format="wav",
            duration=10.0,  # 10 second audio
            sample_rate=None,
            channels=None,
        )

        # Test cost estimation
        inputs = KlingVideoAiAvatarV2ProInput(
            image=image_artifact,
            audio=audio_artifact,
        )
        estimated_cost = await self.generator.estimate_cost(inputs)

        # $0.115/second * 10 seconds = $1.15
        assert estimated_cost == pytest.approx(1.15, rel=0.01)
        assert estimated_cost > 0.0
        assert estimated_cost < 10.0  # Should be under $10 for 10 seconds
