"""
Shared fixtures for generator tests, especially live API tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from boards.config import settings
from boards.generators.artifacts import AudioArtifact, ImageArtifact, TextArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, ProgressUpdate
from boards.logging import get_logger

logger = get_logger(__name__)


def check_api_key(key_name: str) -> bool:
    """
    Check if an API key is available.

    Checks both os.environ and settings.generator_api_keys.

    Args:
        key_name: Name of the API key environment variable

    Returns:
        True if the key is available, False otherwise
    """
    # Check direct environment variable
    if os.getenv(key_name):
        return True

    # Check settings.generator_api_keys
    if settings.generator_api_keys.get(key_name):
        return True

    return False


@pytest.fixture
def skip_if_no_replicate_key():
    """Skip test if REPLICATE_API_TOKEN is not available."""
    if not check_api_key("REPLICATE_API_TOKEN"):
        pytest.skip("REPLICATE_API_TOKEN not set, skipping live API test")


@pytest.fixture
def skip_if_no_fal_key():
    """Skip test if FAL_KEY is not available."""
    if not check_api_key("FAL_KEY"):
        pytest.skip("FAL_KEY not set, skipping live API test")


@pytest.fixture
def skip_if_no_openai_key():
    """Skip test if OPENAI_API_KEY is not available."""
    if not check_api_key("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set, skipping live API test")


@pytest.fixture
def skip_if_no_kie_key():
    """Skip test if KIE_API_KEY is not available."""
    if not check_api_key("KIE_API_KEY"):
        pytest.skip("KIE_API_KEY not set, skipping live API test")


class DummyGeneratorContext(GeneratorExecutionContext):
    """
    Minimal GeneratorExecutionContext for testing.

    This implementation provides stub methods for all required context operations.
    Tests that need custom behavior should subclass or create their own context.
    """

    generation_id: str = "test_generation_id"
    provider_correlation_id: str = "test_correlation_id"
    tenant_id: str = "test_tenant_id"
    board_id: str = "test_board_id"

    async def resolve_artifact(self, artifact: Any) -> str:
        """Return empty string for artifact resolution."""
        return ""

    async def store_image_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        output_index: int = 0,
    ) -> ImageArtifact:
        """Store image result and return artifact."""
        return ImageArtifact(
            generation_id=self.generation_id,
            storage_url=storage_url,
            width=width,
            height=height,
            format=format,
        )

    async def store_video_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        duration: float | None = None,
        fps: float | None = None,
        output_index: int = 0,
    ) -> VideoArtifact:
        """Store video result and return artifact."""
        return VideoArtifact(
            generation_id=self.generation_id,
            storage_url=storage_url,
            width=width,
            height=height,
            duration=duration or 0.0,
            format=format,
            fps=fps,
        )

    async def store_audio_result(
        self,
        storage_url: str,
        format: str,
        duration: float | None = None,
        sample_rate: int | None = None,
        channels: int | None = None,
        output_index: int = 0,
    ) -> AudioArtifact:
        """Store audio result and return artifact."""
        return AudioArtifact(
            generation_id=self.generation_id,
            storage_url=storage_url,
            duration=duration or 0.0,
            format=format,
            sample_rate=sample_rate,
            channels=channels,
        )

    async def store_text_result(
        self,
        content: str,
        format: str,
        output_index: int = 0,
    ) -> TextArtifact:
        """Store text result and return artifact."""
        return TextArtifact(
            generation_id=self.generation_id,
            storage_url="",  # Dummy URL for testing
            format=format,
            content=content,
        )

    async def publish_progress(self, update: ProgressUpdate) -> None:
        """Log progress updates."""
        logger.info(
            "progress_update",
            generation_id=self.generation_id,
            status=update.status,
            message=update.message,
            progress=update.progress,
        )

    async def set_external_job_id(self, external_id: str) -> None:
        """Log external job ID."""
        logger.info(
            "external_job_id_set",
            generation_id=self.generation_id,
            external_id=external_id,
        )


@pytest.fixture
def dummy_context() -> DummyGeneratorContext:
    """
    Provide a dummy generator execution context for testing.

    This context can be used for both unit tests and live API tests.
    """
    return DummyGeneratorContext()


def log_estimated_cost(generator_name: str, estimated_cost: float | None) -> None:
    """
    Log the estimated cost before running a live API test.

    Args:
        generator_name: Name of the generator being tested
        estimated_cost: Estimated cost in USD (or None if unknown)
    """
    if estimated_cost is not None:
        logger.warning(
            "live_api_test_cost",
            generator=generator_name,
            estimated_cost_usd=estimated_cost,
            message=(
                f"Running live API test for {generator_name}. "
                f"Estimated cost: ${estimated_cost:.4f} USD"
            ),
        )
    else:
        logger.warning(
            "live_api_test_cost",
            generator=generator_name,
            estimated_cost_usd=None,
            message=f"Running live API test for {generator_name}. Cost unknown.",
        )


@pytest.fixture
def cost_logger():
    """
    Provide a cost logging function for live API tests.

    Usage:
        def test_something(cost_logger):
            cost_logger("replicate-flux-pro", 0.05)
            # ... run test
    """
    return log_estimated_cost


class ImageResolvingContext(GeneratorExecutionContext):
    """
    Context that can resolve image artifacts by downloading them.

    This is needed for image-to-image and image-to-video generators
    that require input images to be downloaded as local files.
    """

    generation_id: str = "test_generation_id"
    provider_correlation_id: str = "test_correlation_id"
    tenant_id: str = "test_tenant_id"
    board_id: str = "test_board_id"

    async def resolve_artifact(self, artifact: ImageArtifact) -> str:
        """Download the artifact to a temporary file and return the path."""
        import aiohttp

        # Download the image to a temporary file
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"test_image_{artifact.generation_id}.{artifact.format}"

        async with aiohttp.ClientSession() as session:
            async with session.get(artifact.storage_url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download image: {response.status}")

                content = await response.read()
                temp_path.write_bytes(content)

        return str(temp_path)

    async def store_image_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        output_index: int = 0,
    ) -> ImageArtifact:
        """Store image result and return artifact."""
        return ImageArtifact(
            generation_id=self.generation_id,
            storage_url=storage_url,
            width=width,
            height=height,
            format=format,
        )

    async def store_video_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        duration: float | None = None,
        fps: float | None = None,
        output_index: int = 0,
    ) -> VideoArtifact:
        """Store video result and return artifact."""
        return VideoArtifact(
            generation_id=self.generation_id,
            storage_url=storage_url,
            width=width,
            height=height,
            duration=duration or 0.0,
            format=format,
            fps=fps,
        )

    async def store_audio_result(
        self,
        storage_url: str,
        format: str,
        duration: float | None = None,
        sample_rate: int | None = None,
        channels: int | None = None,
        output_index: int = 0,
    ) -> AudioArtifact:
        """Store audio result and return artifact."""
        return AudioArtifact(
            generation_id=self.generation_id,
            storage_url=storage_url,
            duration=duration or 0.0,
            format=format,
            sample_rate=sample_rate,
            channels=channels,
        )

    async def store_text_result(
        self,
        content: str,
        format: str,
        output_index: int = 0,
    ) -> TextArtifact:
        """Store text result and return artifact."""
        return TextArtifact(
            generation_id=self.generation_id,
            storage_url="",  # Dummy URL for testing
            format=format,
            content=content,
        )

    async def publish_progress(self, update: ProgressUpdate) -> None:
        """Log progress updates."""
        logger.info(
            "progress_update",
            generation_id=self.generation_id,
            status=update.status,
            message=update.message,
            progress=update.progress,
        )

    async def set_external_job_id(self, external_id: str) -> None:
        """Log external job ID."""
        logger.info(
            "external_job_id_set",
            generation_id=self.generation_id,
            external_id=external_id,
        )


@pytest.fixture
def image_resolving_context() -> ImageResolvingContext:
    """
    Provide a context that can download and resolve image artifacts.

    This fixture is useful for testing image-to-image and image-to-video
    generators that require input images to be provided as local file paths.

    Usage:
        async def test_image_generator(image_resolving_context):
            artifact = ImageArtifact(
                generation_id="test",
                storage_url="https://example.com/image.png",
                format="png",
                width=256,
                height=256,
            )
            result = await generator.generate(inputs, image_resolving_context)
    """
    return ImageResolvingContext()
