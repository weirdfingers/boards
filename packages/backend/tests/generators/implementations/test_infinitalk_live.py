"""
Live API tests for FalInfinitalkGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_infinitalk_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_infinitalk_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v

Note: These tests use example image and audio URLs from publicly accessible sources
since the generator requires artifact inputs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import AudioArtifact, ImageArtifact
from boards.generators.implementations.fal.video.infinitalk import (
    FalInfinitalkGenerator,
    InfinitalkInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestInfinitalkGeneratorLive:
    """Live API tests for FalInfinitalkGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalInfinitalkGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic talking avatar generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal settings (480p, 145 frames) to reduce cost.

        Note: Uses example image and audio from publicly accessible sources.
        """
        # Create artifacts using example URLs
        # Using a sample portrait image
        image_artifact = ImageArtifact(
            generation_id="example_image",
            storage_url="https://placehold.co/512x512/ffcccc/333333.png",
            format="png",
            width=512,
            height=512,
        )

        # Using example audio from Fal.ai docs
        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://fal.media/files/lion/vyFWygmZsIZlUO4s0nr2n.wav",
            format="wav",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Create minimal input to reduce cost
        inputs = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="A person speaking",
            num_frames=145,  # Default (minimum recommended)
            resolution="480p",  # Lower resolution for cost
            acceleration="regular",  # Default
            seed=42,
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
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp4"
        assert artifact.width == 854  # 480p width
        assert artifact.height == 480
        assert artifact.duration is not None
        assert artifact.duration > 0
        assert artifact.fps is not None
        assert artifact.fps > 0

    @pytest.mark.asyncio
    async def test_generate_with_different_params(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger
    ):
        """
        Test generation with different parameters.

        Tests 720p resolution and different acceleration settings.
        Note: This will cost more due to higher resolution.
        """
        # Create artifacts using example URLs
        image_artifact = ImageArtifact(
            generation_id="example_image",
            storage_url="https://placehold.co/512x512/ccffcc/333333.png",
            format="png",
            width=512,
            height=512,
        )

        audio_artifact = AudioArtifact(
            generation_id="example_audio",
            storage_url="https://fal.media/files/lion/vyFWygmZsIZlUO4s0nr2n.wav",
            format="wav",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        # Test with different parameters
        inputs = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="A person speaking with expression",
            num_frames=200,  # More frames
            resolution="720p",  # Higher resolution
            acceleration="high",  # Faster generation
            seed=999,
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
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp4"
        assert artifact.width == 1280  # 720p width
        assert artifact.height == 720
        assert artifact.duration is not None
        assert artifact.fps is not None

    @pytest.mark.asyncio
    async def test_estimate_cost_matches_pricing(self, skip_if_no_fal_key):
        """
        Test that cost estimation is reasonable.

        This doesn't make an API call, just verifies the cost estimate logic.
        """
        # Create dummy artifacts (not actually used for cost estimation)
        image_artifact = ImageArtifact(
            generation_id="test",
            storage_url="https://example.com/test.jpg",
            format="jpg",
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

        # Test base cost (480p, default frames)
        inputs_base = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test",
        )
        cost_base = await self.generator.estimate_cost(inputs_base)

        # Test 720p cost
        inputs_720p = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test",
            resolution="720p",
        )
        cost_720p = await self.generator.estimate_cost(inputs_720p)

        # Test more frames cost
        inputs_more_frames = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test",
            num_frames=290,  # 2x default
        )
        cost_more_frames = await self.generator.estimate_cost(inputs_more_frames)

        # Verify 720p is 1.5x more expensive than 480p
        assert cost_720p == pytest.approx(cost_base * 1.5, rel=0.01)

        # Verify double frames is 2x more expensive
        assert cost_more_frames == pytest.approx(cost_base * 2.0, rel=0.01)

        # Verify costs are in reasonable range
        assert cost_base > 0.0
        assert cost_base < 1.0  # Should be well under $1 per generation
        assert cost_720p < 2.0
        assert cost_more_frames < 2.0
