"""
Live API tests for FalBytedanceSeedreamV5LiteEditGenerator.

These tests make actual API calls to the Fal.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_fal to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"FAL_KEY": "..."}'
    pytest tests/generators/implementations/test_bytedance_seedream_v5_lite_edit_live.py \
        -v -m live_api

Or using direct environment variable:
    export FAL_KEY="..."
    pytest tests/generators/implementations/test_bytedance_seedream_v5_lite_edit_live.py \
        -v -m live_fal

Or run all Fal live tests:
    pytest -m live_fal -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import ImageArtifact
from boards.generators.implementations.fal.image.bytedance_seedream_v5_lite_edit import (
    BytedanceSeedreamV5LiteEditInput,
    FalBytedanceSeedreamV5LiteEditGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_fal]


class TestBytedanceSeedreamV5LiteEditGeneratorLive:
    """Live API tests for FalBytedanceSeedreamV5LiteEditGenerator using real Fal.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = FalBytedanceSeedreamV5LiteEditGenerator()
        # Sync API keys from settings to os.environ for third-party SDKs
        initialize_generator_api_keys()

    @pytest.fixture
    def test_image_artifact(self):
        """Provide a sample image artifact for testing."""
        return ImageArtifact(
            generation_id="test_input",
            storage_url="https://placehold.co/512x512/ff9900/ffffff.png",
            format="png",
            width=512,
            height=512,
        )

    @pytest.mark.asyncio
    async def test_generate_basic(
        self, skip_if_no_fal_key, image_resolving_context, cost_logger, test_image_artifact
    ):
        """
        Test basic image editing with minimal parameters.

        This test makes a real API call to Fal.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Create minimal input to reduce cost
        inputs = BytedanceSeedreamV5LiteEditInput(
            prompt="Make the background blue",
            image_sources=[test_image_artifact],
            num_images=1,
            image_size="square",
        )

        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        # Execute generation
        result = await self.generator.generate(inputs, image_resolving_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert isinstance(artifact, ImageArtifact)
        assert artifact.storage_url is not None
        assert len(artifact.storage_url) > 0
        # Storage URLs can be HTTPS URLs or data URIs
        if artifact.width is not None:
            assert artifact.width > 0
        if artifact.height is not None:
            assert artifact.height > 0
