"""
Live API tests for FalGrokImagineVideoReferenceToVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    pytest tests/generators/implementations/\
        test_fal_grok_imagine_video_reference_to_video_live.py \
        -v -m live_api

Note: Video generation is expensive. These tests use minimal settings to reduce costs.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.video.grok_imagine_video_reference_to_video import (
    FalGrokImagineVideoReferenceToVideoGenerator,
    GrokImagineVideoReferenceToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFalGrokImagineVideoReferenceToVideoGeneratorLive:
    """Live API tests for FalGrokImagineVideoReferenceToVideoGenerator."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalGrokImagineVideoReferenceToVideoGenerator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
    ):
        """
        Test basic reference-to-video generation with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses 480p resolution, shortest duration, and a single reference image.
        """
        ref_images = [
            ImageArtifact(
                generation_id="test_ref_1",
                storage_url="https://placehold.co/512x512/228B22/ffffff.png?text=Tree",
                format="png",
                width=512,
                height=512,
            ),
        ]

        inputs = GrokImagineVideoReferenceToVideoInput(
            prompt=(
                "A beautiful green tree @Image1 swaying gently "
                "in the wind on a sunny day with blue sky"
            ),
            reference_images=ref_images,
            duration=2,
            aspect_ratio="16:9",
            resolution="480p",
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, image_resolving_context)

        assert result.outputs is not None
        assert len(result.outputs) == 1

        from boards.generators.artifacts import VideoArtifact

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "mp4"
