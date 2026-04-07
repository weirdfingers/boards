"""
Live API tests for FalQwenImage2ProEditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_qwen_image_2_pro_edit_live.py -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_qwen_image_2_pro_edit_live.py -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.qwen_image_2_pro_edit import (
    FalQwenImage2ProEditGenerator,
    QwenImage2ProEditInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestQwenImage2ProEditGeneratorLive:
    """Live API tests for FalQwenImage2ProEditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalQwenImage2ProEditGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_fal_key, image_resolving_context, cost_logger):
        """
        Test basic image editing with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses a small publicly accessible test image to minimize cost.
        """
        test_image_url = "https://placehold.co/512x512/ff9900/ffffff.png"

        test_artifact = ImageArtifact(
            generation_id="test_input",
            storage_url=test_image_url,
            format="png",
            width=512,
            height=512,
        )

        inputs = QwenImage2ProEditInput(
            prompt="Add a blue border around the image",
            image_urls=[test_artifact],
            num_images=1,
            output_format="jpeg",
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
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        assert len(artifact.storage_url) > 0
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
        assert artifact.format == "jpeg"
