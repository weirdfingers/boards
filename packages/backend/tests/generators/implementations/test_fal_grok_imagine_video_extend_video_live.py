"""
Live API tests for FalGrokImagineVideoExtendVideoGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    pytest tests/generators/implementations/\
        test_fal_grok_imagine_video_extend_video_live.py -v -m live_api

Note: Video generation is expensive. These tests use minimal settings to reduce costs.
This test first generates a short video using the reference-to-video endpoint,
then uses that output as input for the extend-video endpoint.
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.implementations.fal.video.grok_imagine_video_extend_video import (
    FalGrokImagineVideoExtendVideoGenerator,
    GrokImagineVideoExtendVideoInput,
)
from boards.generators.implementations.fal.video.grok_imagine_video_reference_to_video import (
    FalGrokImagineVideoReferenceToVideoGenerator,
    GrokImagineVideoReferenceToVideoInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestFalGrokImagineVideoExtendVideoGeneratorLive:
    """Live API tests for FalGrokImagineVideoExtendVideoGenerator."""

    def setup_method(self):
        """Set up generators and ensure API keys are synced to environment."""
        self.generator = FalGrokImagineVideoExtendVideoGenerator()
        self.ref_generator = FalGrokImagineVideoReferenceToVideoGenerator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(
        self,
        skip_if_no_fal_key,
        image_resolving_context,
        cost_logger,
    ):
        """
        Test basic video extension with minimal parameters.

        This test first generates a short video using the reference-to-video
        endpoint, then extends it. This ensures the input video is in the
        correct format expected by the API.
        """
        # Step 1: Generate a short source video using reference-to-video
        ref_images = [
            ImageArtifact(
                generation_id="test_ref_1",
                storage_url="https://placehold.co/512x512/228B22/ffffff.png?text=Tree",
                format="png",
                width=512,
                height=512,
            ),
        ]

        ref_inputs = GrokImagineVideoReferenceToVideoInput(
            prompt=(
                "A beautiful green tree @Image1 swaying gently "
                "in the wind on a sunny day with blue sky"
            ),
            reference_images=ref_images,
            duration=2,
            aspect_ratio="16:9",
            resolution="480p",
        )

        ref_result = await self.ref_generator.generate(ref_inputs, image_resolving_context)
        source_video = ref_result.outputs[0]
        assert isinstance(source_video, VideoArtifact)

        # Step 2: Use the generated video as input for extend-video
        video_artifact = VideoArtifact(
            generation_id="test_source_video",
            storage_url=source_video.storage_url,
            format="mp4",
            width=source_video.width or 848,
            height=source_video.height or 480,
            duration=source_video.duration or 2.0,
            fps=source_video.fps,
        )

        inputs = GrokImagineVideoExtendVideoInput(
            prompt="The tree continues to sway as clouds slowly drift across the bright blue sky",
            video=video_artifact,
            duration=2,
        )

        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, image_resolving_context)

        assert result.outputs is not None
        assert len(result.outputs) == 1

        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.width is not None and artifact.width > 0
        assert artifact.height is not None and artifact.height > 0
        assert artifact.format == "mp4"
